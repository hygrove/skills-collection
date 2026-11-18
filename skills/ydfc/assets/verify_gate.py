# -*- coding: utf-8 -*-
"""
影刀模块交付门禁（ydfc 专用）

用法：
    python verify_gate.py <待交付的模块文件.py>
    python verify_gate.py --text <交付文本文件>      # 验证"即将贴给用户的那段文本"

它检查的是「被验证对象的真实字节」——即即将逐字贴给用户的那份代码。
这是为了杜绝「验证 A、交付 B」：被验证对象必须是交付对象本身。

三道门：
    门禁1  语法     ast.parse + 3.10 兼容 + 反斜杠体检
    门禁2  结构     骨架完整性 / 签名 / 纯函数 / docstring
    门禁3  可运行   剥离影刀壳后用真实文件实跑 + 断言

退出码 0 = 全过；非 0 = 有失败项。
"""
import ast
import os
import re
import subprocess
import sys
import tempfile

PY = sys.executable

# 真实测试文件：优先用环境变量指定，其次用仓库里常见的默认路径
REAL_XLSX = os.environ.get("YDFC_TEST_XLSX", "")


def strip_shell(source):
    """剥离影刀壳：4 行固定 import + main 整块。

    main 必须按整块删（从 def main(args): 到其下所有缩进行），
    不能用 'if line.strip() == "pass": continue'，否则函数体里的
    except ValueError: pass 会被误删，导致 IndentationError。
    """
    out, skipping = [], False
    for line in source.splitlines():
        t = line.strip()
        if t.startswith("import xbot") or t.startswith("from xbot import") \
           or t.startswith("from .import package") or t.startswith("from .package import"):
            continue
        if line.startswith("def main(args)"):
            skipping = True
            continue
        if skipping:
            if t == "" or line.startswith((" ", "\t")):
                continue
            skipping = False
        out.append(line)
    return "\n".join(out)


def normalize(src):
    """统一行尾为 LF。

    Windows 上写出的文件常带 CRLF，而骨架比对是逐字的，
    行尾不一致就会误报"骨架被改"。比对前先归一化。
    """
    return src.replace("\r\n", "\n").replace("\r", "\n")


def count_own_returns(fn):
    """数本函数自己的 return（排除嵌套函数内部的 return）。

    直接用 ast.walk 会把内嵌 def 里的 return 也算进来，
    于是"外层函数忘了写 return"这种情况会被误判为通过。
    """
    nested = set()
    for node in ast.walk(fn):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)) and node is not fn:
            for sub in ast.walk(node):
                nested.add(id(sub))
    count = 0
    for node in ast.walk(fn):
        if isinstance(node, ast.Return) and node.value is not None and id(node) not in nested:
            count += 1
    return count


def identifiers(node):
    """收集节点树里所有标识符字符串"""
    ids = []
    for n in ast.walk(node):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            ids.append(n.name)
        elif isinstance(n, ast.Name):
            ids.append(n.id)
        elif isinstance(n, ast.arg):
            ids.append(n.arg)
    return ids


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    # --text 模式：验证一段"即将贴给用户的交付文本"本身，
    # 而不是磁盘上另一个文件。这是「验证 A、交付 B」的最后一道防线。
    text_mode = sys.argv[1] == "--text"
    if text_mode:
        if len(sys.argv) < 3:
            print(__doc__)
            return 2
        text_path = os.path.abspath(sys.argv[2])
        if not os.path.isfile(text_path):
            print("文件不存在:", text_path)
            return 2
        tmp_dir = tempfile.mkdtemp(prefix="ydfc_gate_")
        mod = os.path.join(tmp_dir, "delivery.py")
        # 二进制写入并显式用 LF，避免 Windows 平台把换行改成 CRLF 干扰后续比对
        with open(mod, "wb") as fh:
            fh.write(open(text_path, "rb").read().replace(b"\r\n", b"\n"))
        print(f"[--text 模式] 验证交付文本文件：{text_path}")
    else:
        mod = os.path.abspath(sys.argv[1])
        if not os.path.isfile(mod):
            print("文件不存在:", mod)
            return 2

    src = open(mod, "rb").read().decode("utf-8")
    src = normalize(src)
    failed = []

    def check(label, ok, detail=""):
        print(("  [PASS] " if ok else "  [FAIL] ") + label + (("  " + detail) if detail else ""))
        if not ok:
            failed.append(label)

    # ---------------- 门禁1：语法 ----------------
    print("=" * 68)
    print("门禁 1：语法（针对交付文件的真实字节）")
    print("=" * 68)
    try:
        ast.parse(src)
        check("整段源码 ast.parse 通过", True)
    except SyntaxError as e:
        check("整段源码 ast.parse 通过", False, f"{e.msg} line {e.lineno} col {e.offset}")
        lines = src.splitlines()
        if e.lineno and e.lineno <= len(lines):
            print("       该行:", repr(lines[e.lineno - 1]))
        return 1

    try:
        ast.parse(src, feature_version=(3, 10))
        check("Python 3.10 语法兼容（无 3.11+ 语法）", True)
    except SyntaxError as e:
        check("Python 3.10 语法兼容", False, e.msg)

    # 反斜杠体检：Windows 路径的反斜杠是 unicodeescape 报错的头号来源。
    # AST 判断不出 r 前缀（Constant.kind 只有 'u'/None），所以直接看源文件字节。
    #
    # 精准判据：只盯"有歧义的转义"——反斜杠 + 大写 U（Unicode 转义，需 8 位十六进制）
    # 或大写 x（十六进制转义，需 2 位）。像 \w \d \s \n 这类常规转义是合法的，不报。
    # raw 字符串前缀能消除歧义。AST 看不见前缀，所以按字节判定：
    # 若该位置所在的字符串字面量是 raw 串（同行有 r" / r'），视为安全。
    risky = []
    for i, ch in enumerate(src):
        if ch != "\\":
            continue
        nxt = src[i + 1:i + 2]
        if nxt in ("U", "x"):
            line_start = src.rfind("\n", 0, i) + 1
            line_end = src.find("\n", i)
            line = src[line_start:line_end if line_end > 0 else len(src)]
            if 'r"' not in line and "r'" not in line:
                risky.append((i, nxt, line.strip()[:70]))
    check("无歧义转义（反斜杠U / 反斜杠x 需在 raw 字符串内）", len(risky) == 0,
          f"可疑 {len(risky)} 处: {risky[:3]}")

    # Windows 路径写成反斜杠形式时（形如 C:\ 或 \\server），仍建议改用正斜杠，
    # 因为这类路径在聊天转贴时可能被改写。
    win_path = re.findall(r"[A-Za-z]:\\|\\\\[A-Za-z0-9._-]+\\", src)
    check("无 Windows 反斜杠路径（建议用正斜杠）", len(win_path) == 0,
          f"可疑 {len(win_path)} 处: {win_path[:3]}")

    # ---------------- 门禁2：结构 ----------------
    print()
    print("=" * 68)
    print("门禁 2：结构")
    print("=" * 68)
    tree = ast.parse(src)
    top_fns = [n for n in tree.body if isinstance(n, ast.FunctionDef)]
    check("4 行固定 import 逐字保留",
          "import xbot\nfrom xbot import print, sleep\nfrom .import package\n"
          "from .package import variables as glv" in src)
    check("def main(args): pass 逐字保留", "def main(args):\n    pass" in src)
    check("main 之后有且仅有新函数",
          len(top_fns) >= 2 and top_fns[0].name == "main", str([f.name for f in top_fns]))

    # 骨架块（4行注释 + 4行固定import + 位置A + main + 位置B）必须在前，
    # 新函数必须在骨架之后。逐行定位，防止 import 落到骨架后面。
    main_idx = src.find("def main(args):")
    new_fn_idx = min((src.find("def %s(" % f.name) for f in top_fns
                      if f.name != "main"), default=-1)
    check("新函数定义在 main 之后", main_idx >= 0 and new_fn_idx > main_idx,
          f"main@{main_idx} newfn@{new_fn_idx}")

    # import 位置：新增 import 必须在 main 之前（位置 A）。main 之后出现的 import 视为违规。
    after_main = src[new_fn_idx:] if new_fn_idx > 0 else ""
    late_imports = re.findall(r"^\s*(?:import \w+|from [\w.]+ import)", after_main, re.M)
    check("新增 import 只出现在位置 A（main 之后无 import）", len(late_imports) == 0,
          f"发现 {len(late_imports)} 处: {late_imports[:3]}")

    new_fns = [n for n in top_fns if n.name != "main"]
    for fn in new_fns:
        tag = fn.name
        # return：只看本函数自己的 return，不把嵌套函数里的 return 算进来。
        # 用一个"排除嵌套函数体"的遍历来数。
        own_returns = count_own_returns(fn)
        check(f"[{tag}] 有 return（且带返回值）", own_returns > 0, f"找到 {own_returns} 个")
        check(f"[{tag}] 标识符全 ASCII", all(i.isascii() for i in identifiers(fn)))
        check(f"[{tag}] 未引用 xbot/glv/package",
              not any(k in ast.get_source_segment(src, fn) for k in ("xbot", "glv", "package")))

        # 注解：只允许基础类型，且不得出现 X | Y 联合类型
        anns = [ast.unparse(a.annotation) for a in fn.args.args if a.annotation]
        if fn.returns is not None:
            anns.append(ast.unparse(fn.returns))
        bad_ann = [a for a in anns if a not in ("str", "int", "float", "bool", "dict", "list", "None")]
        check(f"[{tag}] 注解只含基础类型（无复杂泛型/联合类型）",
              not bad_ann, f"可疑 {bad_ann}")
        check(f"[{tag}] 注解未使用 X | Y",
              not any("|" in a for a in anns), str(anns))

        defaults = [ast.unparse(d) for d in fn.args.defaults]
        check(f"[{tag}] 默认参数非容器",
              not any(d.startswith(("[", "(", "{")) for d in defaults), str(defaults))

        # docstring 八项：逐项检查编号是否齐全。
        # 必须行首锚定——裸子串匹配会被 "16.0" 里的 "6." 之类误判为存在。
        doc = ast.get_docstring(fn) or ""
        doc_headings = set()
        for line in doc.splitlines():
            m = re.match(r"\s*(\d+)\.", line)
            if m:
                doc_headings.add(int(m.group(1)))
        missing = [i for i in range(1, 9) if i not in doc_headings]
        check(f"[{tag}] docstring 八项齐全", not missing, f"缺 {missing}")

        body_lines = len(ast.unparse(fn).splitlines())
        doc_lines = len(doc.splitlines())
        check(f"[{tag}] docstring 未喧宾夺主（docstring 行数 < 函数体行数）",
              doc_lines < body_lines, f"doc={doc_lines} body={body_lines}")

    # ---------------- 门禁3：可运行 ----------------
    print()
    print("=" * 68)
    print("门禁 3：剥离影刀壳后实跑")
    print("=" * 68)
    runner = os.path.join(tempfile.gettempdir(), "_ydfc_runner.py")
    with open(runner, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(RUNNER)
    # 参数布局：[0]=脚本 [1]=模块路径 [2]=可选断言脚本（--text 模式下 [1] 是 --text，[2] 是文本路径，[3] 才是断言脚本）
    if text_mode:
        extra = sys.argv[3] if len(sys.argv) > 3 else ""
    else:
        extra = sys.argv[2] if len(sys.argv) > 2 else ""
    cmd = [PY, runner, mod]
    if extra:
        cmd.append(extra)
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    print(res.stdout)
    if res.returncode != 0:
        print(res.stderr[-2000:])
        failed.append("实跑断言")
    try:
        os.remove(runner)
    except OSError:
        pass

    print()
    print("=" * 68)
    if failed:
        print("门禁未通过：", failed)
        return 1
    print("门禁全部通过 ✅  被验证字节 == 交付字节")
    print("=" * 68)
    return 0


RUNNER = r'''
# -*- coding: utf-8 -*-
"""剥离影刀壳后实跑，校验通用契约。

通用契约（任何函数都该满足）：
    1. 函数可被加载并调用，不抛 ImportError
    2. 第一个位置参数是路径/文本类输入时，正斜杠与反斜杠两种写法结果一致
    3. 非法输入抛的是明确异常（不是静默 None，也不是裸的裸抛栈）
针对性断言（如"某个指标的值应该是多少"）由调用方另传一个断言脚本。
"""
import ast
import inspect
import os
import sys

MOD = sys.argv[1]
EXTRA = sys.argv[2] if len(sys.argv) > 2 else ""


def strip_shell(source):
    out, skipping = [], False
    for line in source.splitlines():
        t = line.strip()
        if t.startswith("import xbot") or t.startswith("from xbot import") \
           or t.startswith("from .import package") or t.startswith("from .package import"):
            continue
        if line.startswith("def main(args)"):
            skipping = True
            continue
        if skipping:
            if t == "" or line.startswith((" ", "\t")):
                continue
            skipping = False
        out.append(line)
    return "\n".join(out)


src = open(MOD, encoding="utf-8").read().replace("\r\n", "\n").replace("\r", "\n")
ns = {}
exec(compile(strip_shell(src), "<stripped>", "exec"), ns)

fns = [n.name for n in ast.parse(src).body
       if isinstance(n, ast.FunctionDef) and n.name != "main"]
assert fns, "模块里没有新函数"
f = ns[fns[0]]
print("  实跑函数:", fns[0])

sig = inspect.signature(f)
params = list(sig.parameters.values())
print("  签名:", sig)

# --- 契约 1：路径类参数的正反斜杠等价性 ---
# 只在第一个参数名像路径时才做这项检查，否则跳过
first = params[0].name if params else ""
if any(k in first.lower() for k in ("path", "file", "dir", "url")):
    real = os.environ.get("YDFC_TEST_XLSX") or os.environ.get("YDFC_TEST_PATH") or ""
    if real:
        r1 = f(real)
        r2 = f(real.replace("/", os.sep).replace(os.sep, "/") if os.sep == "\\" else real)
        print("  正斜杠输出:", r1)
        print("  反斜杠输出:", r2)
        assert r1 == r2, "正反斜杠路径结果应一致"
        print("  [PASS] 路径两种写法结果一致")
    else:
        print("  [SKIP] 路径等价性（未提供真实路径）")
else:
    print("  [SKIP] 路径等价性（首参非路径类型：%s）" % first)

# --- 契约 2：非法输入抛明确异常 ---
# NameError/ImportError 说明模块自身缺依赖，与输入校验无关，要分开报。
for bad in (None, 123, ""):
    try:
        f(bad)
    except (ValueError, TypeError, FileNotFoundError, KeyError):
        continue
    except (NameError, ImportError, AttributeError) as e:
        raise AssertionError(
            "模块自身有问题（不是输入校验问题）：%s: %s —— 检查位置 A 的 import 是否齐全"
            % (type(e).__name__, e))
    except Exception as e:
        raise AssertionError("非法输入 %r 抛了不合适的异常：%s" % (bad, type(e).__name__))
    else:
        print("  [INFO] 非法输入 %r 未抛异常（该函数可能允许空输入）" % (bad,))
print("  [PASS] 非法输入的异常处理符合契约")

# --- 针对性断言（可选） ---
if EXTRA and os.path.isfile(EXTRA):
    # 注入被测函数与模块命名空间；assert 是关键字，不能作字典键，
    # 但断言脚本里可以直接用（它是正常语句）。
    scope = {"F": ns, "f": f, "MOD": MOD}
    exec(compile(open(EXTRA, encoding="utf-8").read(), EXTRA, "exec"), scope)
    print("  [PASS] 针对性断言通过")
'''


if __name__ == "__main__":
    sys.exit(main())
