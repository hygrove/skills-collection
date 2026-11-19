# -*- coding: utf-8 -*-
"""
影刀模块交付门禁（ydfc 专用）

用法：
    python verify_gate.py <待交付的模块文件.py> [断言脚本.py]
    python verify_gate.py --text <交付文本文件> [断言脚本.py]

可选参数：
    --python 3.10    目标 Python 版本（默认 3.10；3.7 时额外拦截 3.8+ 语法与常见新 API）
    --fn <函数名>     只验证某个新函数（多函数模块时用于指定针对性断言的作用对象）
    --strict         把 [SKIP]（未测到的检查）也视为未通过

它检查的是「被验证对象的真实字节」——即即将逐字贴给用户的那份代码。
这是为了杜绝「验证 A、交付 B」：被验证对象必须是交付对象本身。

三道门：
    门禁1  语法     ast.parse + 目标版本兼容 + 转义体检 + Windows 路径体检
    门禁2  结构     骨架完整性 / 签名 / 纯函数 / docstring / 影刀参数面板约束
    门禁3  可运行   剥离影刀壳后用真实输入实跑 + 断言

退出码 0 = 全过；非 0 = 有失败项；2 = 用法或文件问题。

本脚本自身兼容 Python 3.7+（不依赖 ast.unparse 等 3.9+ API），
输出统一为 UTF-8 友好文本，避免中文 Windows 下 GBK 控制台崩溃。
"""
import ast
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import tokenize
import warnings

PY = sys.executable


def _deprecated_ast(name):
    """取旧版 AST 节点类（3.7 的 Str / Index），静默其弃用告警。"""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            return getattr(ast, name, None)
    except Exception:
        return None


STR_CLS = _deprecated_ast("Str")
INDEX_CLS = _deprecated_ast("Index")

# 固定骨架：4 行 import 必须逐字保留
SKELETON_IMPORTS = (
    "import xbot\n"
    "from xbot import print, sleep\n"
    "from .import package\n"
    "from .package import variables as glv"
)

BASIC_ANNOTATIONS = {"str", "int", "float", "bool", "dict", "list", "None"}

# 常见「版本敏感 API」：目标版本低于右侧时提示（语法级为主，运行期 API 为辅）
ATTR_API_SINCE = {
    "removeprefix": (3, 9),
    "removesuffix": (3, 9),
    "pairwise": (3, 10),
    "lcm": (3, 9),
    "isqrt": (3, 8),
    "prod": (3, 8),
    "cache": (3, 9),
}
MODULE_SINCE = {
    "graphlib": (3, 9),
    "zoneinfo": (3, 9),
}


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------

def configure_io():
    """让输出在中文 Windows（GBK 控制台）下不崩。

    管道场景强制 UTF-8（父进程按 UTF-8 解码子进程输出）；
    交互终端保留本机编码，只把无法编码的字符替换掉，避免 UnicodeEncodeError。
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            if stream is None:
                continue
            if stream.isatty():
                stream.reconfigure(errors="replace")
            else:
                stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def parse_version(text):
    """'3.7' / '37' / '3.10.11' -> (3, 7)"""
    parts = re.findall(r"\d+", text)
    if len(parts) >= 2:
        return (int(parts[0]), int(parts[1]))
    raise SystemExit("无法解析 --python 版本: %r" % (text,))


def version_str(v):
    return "%d.%d" % v


def read_text_file(path):
    """读交付文件：必须是 UTF-8 且无 BOM。返回 (src, error)。"""
    try:
        raw = open(path, "rb").read()
    except OSError as e:
        return None, "无法读取文件: %s" % e
    if raw.startswith(b"\xef\xbb\xbf"):
        return None, "文件带 UTF-8 BOM（影刀要求 UTF-8 无 BOM），请另存为无 BOM"
    try:
        src = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        return None, "文件不是合法 UTF-8: %s" % e
    return src.replace("\r\n", "\n").replace("\r", "\n"), None


def strip_shell(source):
    """剥离影刀壳：4 行固定 import + main 整块。

    保留行号：被剥离的行替换为空行，这样 AST 与 traceback 的行号
    仍与交付文件一致（门禁3 需要按行号区分"函数自己 raise"还是"底层库 raise"）。
    """
    out, skipping = [], False
    for line in source.splitlines():
        t = line.strip()
        if t.startswith("import xbot") or t.startswith("from xbot import") \
           or t.startswith("from .import package") or t.startswith("from .package import"):
            out.append("")
            continue
        if line.startswith("def main(args)"):
            skipping = True
            out.append("")
            continue
        if skipping:
            if t == "" or line.startswith((" ", "\t")):
                out.append("")
                continue
            skipping = False
        out.append(line)
    return "\n".join(out)


def segment(src, node, fallback=""):
    """取节点源码片段；Python 3.7 没有 ast.get_source_segment，退化为单行截取。"""
    getter = getattr(ast, "get_source_segment", None)
    if getter is not None:
        try:
            seg = getter(src, node)
            if seg is not None:
                return seg
        except Exception:
            pass
    lines = src.splitlines()
    ln = getattr(node, "lineno", None)
    if not ln or ln > len(lines):
        return fallback
    line = lines[ln - 1]
    col = getattr(node, "col_offset", 0)
    end = getattr(node, "end_col_offset", None)
    return line[col:end] if end is not None else line[col:]


def annotation_text(node):
    """注解的可读形态，不依赖 ast.unparse（3.9+）。"""
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return "%s.%s" % (annotation_text(node.value), node.attr)
    if isinstance(node, ast.Subscript):
        return "Subscript"
    if isinstance(node, ast.BinOp):
        return "BinOp"
    if INDEX_CLS is not None and isinstance(node, INDEX_CLS):  # Python 3.7/3.8
        return "Subscript"
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if STR_CLS is not None and isinstance(node, STR_CLS):
        return repr(node.s)
    return type(node).__name__


def collect_identifiers(node):
    """收集函数内所有标识符（含属性名、关键字参数名、异常绑定名）。"""
    ids = []
    for n in ast.walk(node):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ids.append(n.name)
        elif isinstance(n, ast.Name):
            ids.append(n.id)
        elif isinstance(n, ast.arg):
            ids.append(n.arg)
        elif isinstance(n, ast.Attribute):
            ids.append(n.attr)
        elif isinstance(n, ast.keyword) and n.arg:
            ids.append(n.arg)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            ids.extend(n.names)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            ids.append(n.name)
    return ids


def shell_references(node):
    """用 AST 找函数的代码里是否真的引用了影刀壳对象（不看 docstring/注释）。"""
    hits = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name) and n.id in ("xbot", "glv", "package"):
            hits.add(n.id)
        elif isinstance(n, ast.Attribute) and n.attr in ("xbot", "glv", "package"):
            hits.add(n.attr)
        elif isinstance(n, ast.ImportFrom) and n.module and n.module.split(".")[0] in ("xbot", "package"):
            hits.add(n.module)
        elif isinstance(n, ast.Import):
            for alias in n.names:
                if alias.name.split(".")[0] in ("xbot", "package"):
                    hits.add(alias.name)
    return sorted(hits)


def docstring_node(fn):
    if fn.body and isinstance(fn.body[0], ast.Expr):
        val = fn.body[0].value
        if isinstance(val, ast.Constant) and isinstance(val.value, str):
            return fn.body[0]
        if STR_CLS is not None and isinstance(val, STR_CLS):
            return fn.body[0]
    return None


def docstring_text(fn):
    node = docstring_node(fn)
    if node is None:
        return ""
    val = node.value
    if isinstance(val, ast.Constant):
        return val.value if isinstance(val.value, str) else ""
    return getattr(val, "s", "")


# --------------------------------------------------------------------------
# 门禁 1：语法
# --------------------------------------------------------------------------

def check_escapes(src):
    """按 tokenize 的真实字符串字面量检查歧义转义。

    判据：非 raw 字符串里出现 `\\U` 或 `\\x`，且该反斜杠前面是偶数个连续
    反斜杠（即它确实是转义起始符）。`\\\\U`（字面反斜杠+U）视为安全。
    """
    risky = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return risky
    for tok in tokens:
        if tok.type != tokenize.STRING:
            continue
        text = tok.string
        prefix = re.match(r"[A-Za-z]*", text).group(0).lower()
        if "r" in prefix:
            continue
        for m in re.finditer(r"\\[Ux]", text):
            i = m.start()
            n = 0
            j = i - 1
            while j >= 0 and text[j] == "\\":
                n += 1
                j -= 1
            if n % 2:
                continue  # 这个反斜杠本身被转义了，安全
            line = tok.start[0] + text[:i].count("\n")
            risky.append((line, m.group(0), text[max(0, i - 15):i + 10]))
    return risky


def check_windows_paths(src):
    """只看字符串字面量里的 Windows 反斜杠路径（注释不算）。"""
    found = []
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(src).readline))
    except (tokenize.TokenError, IndentationError, SyntaxError):
        return found
    pattern = re.compile(r"[A-Za-z]:\\\\|\\\\\\\\[A-Za-z0-9._-]+\\\\")
    for tok in tokens:
        if tok.type != tokenize.STRING:
            continue
        for m in pattern.finditer(tok.string):
            found.append((tok.start[0] + tok.string[:m.start()].count("\n"), m.group(0)))
    return found


def check_version_api(tree, target):
    """目标版本低于某 API 的引入版本时提示（近似扫描，语法之外的第二道网）。"""
    problems = []

    def too_new(since):
        return target < since

    imported = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            for alias in node.names:
                imported[alias.asname or alias.name] = node.module
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported[alias.asname or alias.name.split(".")[0]] = alias.name

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            root = node.module.split(".")[0]
            if root in MODULE_SINCE and too_new(MODULE_SINCE[root]):
                problems.append((node.lineno, "%s（模块需 Python %s+）"
                                 % (root, version_str(MODULE_SINCE[root]))))
        if isinstance(node, ast.Attribute):
            if node.attr in ATTR_API_SINCE and too_new(ATTR_API_SINCE[node.attr]):
                # 只对已知模块/已导入名字报，避免误伤用户自己的 .cache()
                if isinstance(node.value, ast.Name) and (
                        node.value.id in ("math", "itertools", "functools")
                        or node.value.id in imported):
                    problems.append((node.lineno, "%s（需 Python %s+）"
                                     % (node.attr, version_str(ATTR_API_SINCE[node.attr]))))
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "zip" and too_new((3, 10)):
                if any(kw.arg == "strict" for kw in node.keywords):
                    problems.append((node.lineno, "zip(strict=)（需 Python 3.10+）"))
    return problems


# --------------------------------------------------------------------------
# 门禁 2：结构
# --------------------------------------------------------------------------

def body_code_lines(src, fn):
    """函数体源码行数（排除 docstring 与签名行），用片段估算。"""
    body = fn.body[1:] if docstring_node(fn) is not None else fn.body
    count = 0
    for stmt in body:
        seg = segment(src, stmt)
        count += max(1, len(seg.splitlines()))
    return count


def check_structure(src, tree, report):
    top_fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    if not top_fns:
        report.check("模块里有函数", False)
        return []

    report.check("4 行固定 import 逐字保留", SKELETON_IMPORTS in src)
    report.check("def main(args): pass 逐字保留", "def main(args):\n    pass" in src)
    report.check("main 是第一个函数，其后为新函数",
                 top_fns[0].name == "main" and len(top_fns) >= 2,
                 str([f.name for f in top_fns]))

    main_idx = src.find("def main(args):")
    first_new = None
    for f in top_fns[1:]:
        if f.name != "main":
            first_new = f
            break
    if first_new is not None:
        new_idx = src.find("def %s(" % first_new.name)
        report.check("新函数定义在 main 之后", main_idx >= 0 and new_idx > main_idx,
                     "main@%d new@%d" % (main_idx, new_idx))
        after = src[new_idx:]
        late = re.findall(r"^\s*(?:import \w+|from [\w.]+ import)", after, re.M)
        report.check("新增 import 只出现在位置 A（main 之后无 import）",
                     len(late) == 0, "发现 %d 处: %s" % (len(late), late[:3]))

    new_fns = [f for f in top_fns if f.name != "main"]
    for fn in new_fns:
        tag = fn.name

        own_returns = 0
        nested = set()
        for node in ast.walk(fn):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node is not fn:
                for sub in ast.walk(node):
                    nested.add(id(sub))
        for node in ast.walk(fn):
            if isinstance(node, ast.Return) and node.value is not None and id(node) not in nested:
                own_returns += 1
        report.check("[%s] 有 return（且带返回值）" % tag, own_returns > 0,
                     "找到 %d 个" % own_returns)

        bad_ids = [i for i in collect_identifiers(fn) if not i.isascii()]
        report.check("[%s] 标识符全 ASCII" % tag, not bad_ids, str(bad_ids[:5]))

        refs = shell_references(fn)
        report.check("[%s] 未引用 xbot/glv/package" % tag, not refs, str(refs))

        annotations = [a.annotation for a in fn.args.args if a.annotation]
        if getattr(fn.args, "vararg", None) is not None and fn.args.vararg.annotation:
            annotations.append(fn.args.vararg.annotation)
        if fn.returns is not None:
            annotations.append(fn.returns)
        bad_ann = [annotation_text(a) for a in annotations
                   if annotation_text(a) not in BASIC_ANNOTATIONS]
        report.check("[%s] 注解只含基础类型（无复杂泛型/联合类型）" % tag,
                     not bad_ann, str(bad_ann))
        has_union = any(isinstance(a, ast.BinOp) and isinstance(a.op, ast.BitOr)
                        for a in annotations)
        report.check("[%s] 注解未使用 X | Y" % tag, not has_union,
                     str([annotation_text(a) for a in annotations]))

        container_defaults, comma_defaults = [], []
        for d in fn.args.defaults:
            if isinstance(d, (ast.List, ast.Tuple, ast.Dict, ast.Set,
                              ast.ListComp, ast.DictComp, ast.SetComp, ast.GeneratorExp)):
                container_defaults.append(segment(src, d, "?"))
            value = None
            if isinstance(d, ast.Constant) and isinstance(d.value, str):
                value = d.value
            elif STR_CLS is not None and isinstance(d, STR_CLS):
                value = d.s
            if value is not None and ("," in value or "，" in value):
                comma_defaults.append(value)
        report.check("[%s] 默认参数非容器" % tag, not container_defaults,
                     str(container_defaults))
        report.check("[%s] 默认参数值不含逗号（影刀参数面板会误拆）" % tag,
                     not comma_defaults, str(comma_defaults))

        doc = docstring_text(fn)
        headings = set()
        for line in doc.splitlines():
            m = re.match(r"\s*(\d+)\.", line)
            if m:
                headings.add(int(m.group(1)))
        missing = [i for i in range(1, 9) if i not in headings]
        report.check("[%s] docstring 八项齐全" % tag, not missing, "缺 %s" % missing)

        doc_lines = len(doc.splitlines()) if doc else 0
        code_lines = body_code_lines(src, fn)
        # 八项 docstring 至少 8 行，短函数必然与"行数少于代码"冲突；
        # 预算取 max(10, 代码行数)：小函数给 10 行余量，长函数仍要求 doc 不超过代码。
        budget = max(10, code_lines)
        report.check("[%s] docstring 未喧宾夺主（行数 <= max(10, 代码行数)）" % tag,
                     doc_lines <= budget,
                     "doc=%d code=%d budget=%d" % (doc_lines, code_lines, budget))
    return new_fns


# --------------------------------------------------------------------------
# 门禁 3：剥离壳后实跑
# --------------------------------------------------------------------------

RUNNER = r'''# -*- coding: utf-8 -*-
"""剥离影刀壳后实跑一个函数，校验通用契约。由 verify_gate.py 调用。"""
import ast
import inspect
import os
import sys


def strip_shell(source):
    out, skipping = [], False
    for line in source.splitlines():
        t = line.strip()
        if t.startswith("import xbot") or t.startswith("from xbot import") \
           or t.startswith("from .import package") or t.startswith("from .package import"):
            out.append("")
            continue
        if line.startswith("def main(args)"):
            skipping = True
            out.append("")
            continue
        if skipping:
            if t == "" or line.startswith((" ", "\t")):
                out.append("")
                continue
            skipping = False
        out.append(line)
    return "\n".join(out)


def flag_value(argv, flag, default=None):
    if flag in argv:
        i = argv.index(flag)
        if i + 1 < len(argv):
            return argv[i + 1]
    return default


def main():
    argv = sys.argv[1:]
    if not argv:
        print("runner: 缺少模块路径")
        return 2
    mod = argv[0]
    wanted = flag_value(argv, "--fn")
    asserts = flag_value(argv, "--asserts", "")

    src = open(mod, encoding="utf-8").read()
    src = src.replace("\r\n", "\n").replace("\r", "\n")
    stripped = strip_shell(src)
    ns = {}
    try:
        exec(compile(stripped, "<stripped>", "exec"), ns)
    except Exception as e:
        print("  [FAIL] 剥离影刀壳后模块无法加载: %s: %s" % (type(e).__name__, e))
        return 1

    tree = ast.parse(stripped)
    fns = [n for n in tree.body
           if isinstance(n, ast.FunctionDef) and n.name != "main"]
    if not fns:
        print("  [FAIL] 模块里没有新函数")
        return 1
    node = None
    for f in fns:
        if wanted is None or f.name == wanted:
            node = f
            break
    if node is None:
        print("  [FAIL] 找不到函数:", wanted)
        return 1
    if node.name not in ns:
        print("  [FAIL] 函数未在模块命名空间里定义:", node.name)
        return 1
    f = ns[node.name]
    print("  实跑函数:", node.name)
    try:
        sig = inspect.signature(f)
    except (TypeError, ValueError) as e:
        print("  [FAIL] 无法读取签名:", e)
        return 1
    print("  签名:", sig)

    failed = []

    explicit_raises = set()
    for sub in ast.walk(node):
        if isinstance(sub, ast.Raise):
            explicit_raises.add(sub.lineno)

    params = list(sig.parameters.values())
    P = inspect.Parameter
    required_rest = [p for p in params[1:]
                     if p.default is p.empty
                     and p.kind not in (P.VAR_POSITIONAL, P.VAR_KEYWORD)]
    single_ok = bool(params) and params[0].kind not in (P.VAR_POSITIONAL, P.VAR_KEYWORD)

    def outcome(arg):
        try:
            return ("ok", f(arg))
        except KeyboardInterrupt:
            raise
        except BaseException as e:  # noqa: BLE001 - 契约测试需要观察所有异常
            tb = e.__traceback__
            last = None
            while tb is not None:
                last = tb
                tb = tb.tb_next
            line = None
            if last is not None and last.tb_frame.f_code.co_filename == "<stripped>":
                line = last.tb_lineno
            return ("err", type(e).__name__, str(e), line)

    if not single_ok:
        print("  [SKIP] 契约探测：函数没有可探测的位置参数"
              "（未测到，不等于通过）")
    elif required_rest:
        print("  [SKIP] 契约探测：函数需要 %d 个必填参数，无法用单参数探测"
              "（未测到，不等于通过）" % (1 + len(required_rest)))
    else:
        first = params[0].name.lower()
        path_like = any(k in first for k in
                        ("path", "file", "dir", "url", "xlsx", "xls", "folder", "excel"))
        if path_like:
            real = os.environ.get("YDFC_TEST_XLSX") or os.environ.get("YDFC_TEST_PATH") or ""
            if not real:
                print("  [SKIP] 路径正反斜杠等价性：未设置 YDFC_TEST_XLSX / YDFC_TEST_PATH"
                      "（未测到，不等于通过）")
            else:
                fwd = real.replace(chr(92), "/")
                back = real.replace("/", chr(92))
                if fwd == back:
                    print("  [SKIP] 路径正反斜杠等价性：测试路径不含分隔符，无从区分")
                else:
                    a = outcome(fwd)
                    b = outcome(back)
                    if a[0] == "ok" and b[0] == "ok" and a[1] == b[1]:
                        print("  [PASS] 路径两种写法行为一致")
                    elif a[0] == "err" and b[0] == "err" and a[1] == b[1]:
                        print("  [INFO] 两种写法抛同类异常（%s），只证明了异常类型一致；"
                              "给一个真实可读文件能加强验证" % a[1])
                        print("  [PASS] 路径两种写法行为一致")
                    else:
                        failed.append("路径等价性")
                        print("  [FAIL] 路径两种写法行为不一致")
                        print("         正斜杠:", a)
                        print("         反斜杠:", b)
        else:
            print("  [N/A] 路径正反斜杠等价性：首参不是路径类（%s）" % params[0].name)

        problems = []
        for bad in (None, 123, ""):
            r = outcome(bad)
            if r[0] == "ok":
                print("  [INFO] 非法输入 %r 未抛异常（该函数可能允许空输入）" % (bad,))
                continue
            name, msg, line = r[1], r[2], r[3]
            if name in ("NameError", "ImportError", "ModuleNotFoundError"):
                problems.append("%r 触发 %s：模块自身缺依赖（检查位置 A 的 import）: %s"
                                % (bad, name, msg))
                continue
            expected = ("ValueError", "TypeError", "FileNotFoundError", "KeyError",
                        "OSError", "NotADirectoryError", "PermissionError", "IsADirectoryError")
            if name in expected:
                if line in explicit_raises and not any(
                        "\u4e00" <= ch <= "\u9fff" for ch in msg):
                    problems.append("%r 抛 %s，但异常信息不是中文（规则要求中文说明）: %s"
                                    % (bad, name, msg))
                continue
            if line in explicit_raises:
                problems.append("%r 抛了不合适的异常类型 %s: %s" % (bad, name, msg))
            else:
                print("  [INFO] %r 由底层抛出 %s（建议在函数内转成中文异常）: %s"
                      % (bad, name, msg))
        if problems:
            failed.append("非法输入契约")
            for p in problems:
                print("  [FAIL]", p)
        else:
            print("  [PASS] 非法输入的异常处理符合契约")

    if asserts and os.path.isfile(asserts):
        scope = {"F": ns, "f": f, "MOD": mod, "FN": node.name}
        try:
            code = open(asserts, encoding="utf-8").read()
            exec(compile(code, asserts, "exec"), scope)
        except AssertionError as e:
            failed.append("针对性断言")
            print("  [FAIL] 针对性断言失败:", e)
        except Exception as e:
            failed.append("针对性断言")
            print("  [FAIL] 针对性断言抛异常: %s: %s" % (type(e).__name__, e))
        else:
            print("  [PASS] 针对性断言通过")

    if failed:
        print("  契约未通过:", failed)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


class Reporter(object):
    def __init__(self):
        self.failed = []
        self.skipped = []

    def check(self, label, ok, detail=""):
        print("  [PASS] " + label if ok else "  [FAIL] " + label,
              end="")
        if detail:
            print("  " + detail)
        else:
            print()
        if not ok:
            self.failed.append(label)

    def skip(self, label, reason=""):
        print("  [SKIP] " + label + (("  " + reason) if reason else ""))
        self.skipped.append(label)

    def info(self, text):
        print("  [INFO] " + text)


def parse_args(argv):
    text_mode = False
    python_ver = (3, 10)
    fn = None
    strict = False
    positional = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--text":
            text_mode = True
        elif a == "--strict":
            strict = True
        elif a == "--python":
            i += 1
            if i >= len(argv):
                raise SystemExit("--python 缺少版本号")
            python_ver = parse_version(argv[i])
        elif a.startswith("--python="):
            python_ver = parse_version(a.split("=", 1)[1])
        elif a == "--fn":
            i += 1
            if i >= len(argv):
                raise SystemExit("--fn 缺少函数名")
            fn = argv[i]
        elif a.startswith("--fn="):
            fn = a.split("=", 1)[1]
        elif a in ("-h", "--help"):
            print(__doc__)
            raise SystemExit(0)
        else:
            positional.append(a)
        i += 1
    if not positional:
        print(__doc__)
        raise SystemExit(2)
    target = os.path.abspath(positional[0])
    asserts = os.path.abspath(positional[1]) if len(positional) > 1 else ""
    return text_mode, target, asserts, python_ver, fn, strict


def main(argv=None):
    configure_io()
    if argv is None:
        argv = sys.argv[1:]
    text_mode, target, asserts, python_ver, only_fn, strict = parse_args(argv)

    if not os.path.isfile(target):
        print("文件不存在:", target)
        return 2

    src, err = read_text_file(target)
    if err:
        print("  [FAIL] " + err)
        print("门禁未通过：文件编码")
        return 1
    if text_mode:
        print("[--text 模式] 验证交付文本文件：%s" % target)

    report = Reporter()

    # ---------------- 门禁1：语法 ----------------
    print("=" * 68)
    print("门禁 1：语法（针对交付文件的真实字节，目标 Python %s）" % version_str(python_ver))
    print("=" * 68)
    try:
        tree = ast.parse(src)
        report.check("整段源码 ast.parse 通过", True)
    except SyntaxError as e:
        report.check("整段源码 ast.parse 通过", False,
                     "%s line %s col %s" % (e.msg, e.lineno, e.offset))
        lines = src.splitlines()
        if e.lineno and e.lineno <= len(lines):
            print("       该行:", repr(lines[e.lineno - 1]))
        finish(report, strict)
        return 1

    try:
        ast.parse(src, feature_version=python_ver)
        report.check("Python %s 语法兼容" % version_str(python_ver), True)
    except SyntaxError as e:
        report.check("Python %s 语法兼容" % version_str(python_ver), False, e.msg)
    except TypeError:
        report.skip("Python %s 语法兼容" % version_str(python_ver),
                    "当前解释器不支持 feature_version（需 Python 3.8+）")

    api_problems = check_version_api(tree, python_ver)
    report.check("未使用 %s 之后才有的常见 API" % version_str(python_ver),
                 not api_problems,
                 str(api_problems[:3]) if api_problems else "")

    risky = check_escapes(src)
    report.check("无歧义转义（反斜杠U / 反斜杠x 需在 raw 字符串内）",
                 len(risky) == 0, "可疑 %d 处: %s" % (len(risky), risky[:3]))

    win_paths = check_windows_paths(src)
    report.check("无 Windows 反斜杠路径（建议用正斜杠）",
                 len(win_paths) == 0, "可疑 %d 处: %s" % (len(win_paths), win_paths[:3]))

    # ---------------- 门禁2：结构 ----------------
    print()
    print("=" * 68)
    print("门禁 2：结构")
    print("=" * 68)
    new_fns = check_structure(src, tree, report)

    # ---------------- 门禁3：可运行 ----------------
    print()
    print("=" * 68)
    print("门禁 3：剥离影刀壳后实跑")
    print("=" * 68)

    tmp_dir = tempfile.mkdtemp(prefix="ydfc_gate_")
    try:
        mod = target
        if text_mode:
            mod = os.path.join(tmp_dir, "delivery.py")
            with open(mod, "wb") as fh:
                fh.write(src.encode("utf-8"))
        runner = os.path.join(tmp_dir, "_ydfc_runner.py")
        with open(runner, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(RUNNER)

        targets = [f.name for f in new_fns]
        if only_fn:
            targets = [only_fn]
        if not targets:
            report.check("有可实跑的新函数", False)
        assert_target = only_fn or (targets[0] if targets else None)

        env = dict(os.environ)
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"

        for name in targets:
            print("  --- 函数 %s ---" % name)
            cmd = [PY, runner, mod, "--fn", name]
            if asserts and name == assert_target:
                cmd.extend(["--asserts", asserts])
            try:
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     env=env)
            except OSError as e:
                report.check("[%s] 实跑进程可启动" % name, False, str(e))
                continue
            out = res.stdout.decode("utf-8", "replace") if res.stdout else ""
            err_out = res.stderr.decode("utf-8", "replace") if res.stderr else ""
            if out.strip():
                sys.stdout.write(out if out.endswith("\n") else out + "\n")
                for line in out.splitlines():
                    if "[SKIP]" in line:
                        report.skipped.append(
                            "[%s] %s" % (name, line.split("[SKIP]", 1)[1].strip()))
            if res.returncode != 0:
                if err_out.strip():
                    print(err_out.strip()[-2000:])
                report.failed.append("[%s] 实跑契约" % name)
            if asserts and name != assert_target:
                print("  [INFO] 针对性断言只作用于 %s（可用 --fn 指定）" % assert_target)
        if asserts and targets and assert_target not in targets:
            report.check("断言脚本指定了存在的函数（%s）" % assert_target, False)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return finish(report, strict)


def finish(report, strict=False):
    print()
    print("=" * 68)
    if report.skipped:
        print("被跳过的检查（未测到，不等于通过）：", report.skipped)
    if report.failed:
        print("门禁未通过：", report.failed)
        return 1
    if strict and report.skipped:
        print("门禁未通过（--strict：存在被跳过的检查）")
        return 1
    print("门禁全部通过  被验证字节 == 交付字节")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())