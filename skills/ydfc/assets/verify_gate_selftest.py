# -*- coding: utf-8 -*-
"""
门禁脚本自身的回归测试（verify_gate.py 的反向测试）。

一个只会报 PASS 的门禁等于没有门禁。本脚本用内置样例模块造出各类坏代码，
逐个确认 verify_gate.py 能抓到并以非零退出码失败；同时确认三类"不该抓"的
代码仍然通过（防止门禁误伤）。

用法：
    python verify_gate_selftest.py                # 用内置样例自检
    python verify_gate_selftest.py <你的模块.py>   # 先确认你的模块能过门禁，再自检

设计要点：
    1. 样例模块内置，不依赖外部文件里的变量名/注解形态；
    2. 每条用例先验证"变异确实发生了"（变异后源码 != 样例）；
    3. 临时文件写在系统临时目录，不污染用户工作区。
"""
import ast
import os
import re
import subprocess
import sys
import tempfile

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "verify_gate.py")


def configure_io():
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


GOOD = '''# 使用提醒:
# 1. xbot包提供软件自动化、数据表格、Excel、日志、AI等功能
# 2. package包提供访问当前应用数据的功能，如获取元素、访问全局变量、获取资源文件等功能
# 3. 当此模块作为流程独立运行时执行main函数
# 4. 可视化流程中可以通过"调用模块"的指令使用此模块
import xbot
from xbot import print, sleep
from .import package
from .package import variables as glv

# ===== 位置 A：新增依赖 import 放在这里（固定 4 行之后、def main 之前）=====
# 本函数只用自带功能，无需新增依赖

def main(args):
    pass


# ===== 位置 B：新函数从这里开始追加 =====
def count_lines(path: str, encoding: str = "utf-8") -> int:
    """1. 统计文本文件的行数。
    2. 输入：path 文件路径，如 "C:/data/a.txt"；encoding 编码，默认 utf-8。
    3. 输出：int 行数，如 12。
    4. 调用：count_lines("C:/data/a.txt")。
    5. 输入要求：path 必须是非空字符串；不合法时抛 ValueError。
    6. 依赖：只用标准库，无需装包。
    7. 运行环境：Python 3.10。
    8. 影刀调用：用「调用模块」选 count_lines。
    """
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path 必须是非空字符串")
    if not isinstance(encoding, str) or not encoding:
        raise ValueError("encoding 必须是非空字符串")
    with open(path, "r", encoding=encoding) as fh:
        return len(fh.readlines())
'''


# --------------------------------------------------------------------------
# 变异器：每个返回 (新源码 or None, 期望关键字, 额外参数, 额外环境变量)
# 返回 None 表示"这个变异不适用于当前样例"。
# --------------------------------------------------------------------------

def _strip_own_returns(src):
    """用 AST 删掉新函数自己的 return（保留内嵌函数的）。"""
    tree = ast.parse(src)
    target = None
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name != "main":
            target = node
            break
    if target is None:
        return None
    nested = set()
    for node in ast.walk(target):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not target:
            for sub in ast.walk(node):
                nested.add(id(sub))
    lines = src.splitlines()
    changed = False
    for node in ast.walk(target):
        if isinstance(node, ast.Return) and node.value is not None and id(node) not in nested:
            ln = node.lineno - 1
            indent = len(lines[ln]) - len(lines[ln].lstrip())
            lines[ln] = " " * indent + "pass"
            changed = True
    return "\n".join(lines) + "\n" if changed else None


def _inject_after_docstring(src, code):
    """把 inject 代码插到函数体第一行（docstring 之后）。"""
    m = re.search(r'^\s*"""[\s\S]*?"""\n', src, re.M)
    if not m:
        return None
    return src[:m.end()] + code + src[m.end():]


def build_cases():
    def m_syntax():
        return GOOD.replace("    return len(fh.readlines())",
                            "    return len(fh.readlines()))", 1), "ast.parse", [], {}

    def m_py311():
        return GOOD + "\n\ndef _probe(v):\n    match v:\n        case 1:\n            return 1\n    return 0\n", \
            "3.10 语法兼容", [], {}

    def m_walrus_for_37():
        mutated = _inject_after_docstring(GOOD, "    if (n := 1):\n        pass\n")
        if mutated is None:
            return None
        return mutated, "3.7 语法兼容", ["--python", "3.7"], {}

    def m_no_main():
        mutated = GOOD.replace("def main(args):\n    pass", "# main 没了", 1)
        return (mutated, "main(args)", [], {}) if mutated != GOOD else None

    def m_import_changed():
        mutated = GOOD.replace("from xbot import print, sleep", "from xbot import print", 1)
        return (mutated, "固定 import", [], {}) if mutated != GOOD else None

    def m_import_pos():
        return GOOD + "\nimport json\n", "位置 A", [], {}

    def m_generic_ann():
        mutated = GOOD.replace("-> int:", "-> dict[str, int] | None:", 1)
        return (mutated, "注解只含基础类型", [], {}) if mutated != GOOD else None

    def m_no_return():
        mutated = _strip_own_returns(GOOD)
        return (mutated, "有 return", [], {}) if mutated else None

    def m_docstring():
        mutated = re.sub(r"^\s*6\. .*\n", "", GOOD, count=1, flags=re.M)
        return (mutated, "docstring 八项", [], {}) if mutated != GOOD else None

    def m_cn_ident():
        mutated = GOOD.replace("def count_lines(", "def 统计行数(", 1)
        return (mutated, "ASCII", [], {}) if mutated != GOOD else None

    def m_escape():
        mutated = _inject_after_docstring(GOOD, '    _x = "C:/tmp\\x41.txt"\n')
        return (mutated, "歧义转义", [], {}) if mutated else None

    def m_win_path():
        mutated = _inject_after_docstring(GOOD, '    _p = "C:\\\\tmp\\\\a.txt"\n')
        return (mutated, "反斜杠路径", [], {}) if mutated else None

    def m_container_default():
        mutated = GOOD.replace('encoding: str = "utf-8"',
                               'encoding: str = "utf-8", extra: list = []', 1)
        return (mutated, "默认参数非容器", [], {}) if mutated != GOOD else None

    def m_comma_default():
        mutated = GOOD.replace('encoding: str = "utf-8"',
                               'encoding: str = "utf-8", sep: str = ","', 1)
        return (mutated, "逗号", [], {}) if mutated != GOOD else None

    def m_xbot_use():
        mutated = _inject_after_docstring(GOOD, "    _marker = xbot\n")
        return (mutated, "未引用 xbot", [], {}) if mutated else None

    def m_path_backslash():
        mutated = _inject_after_docstring(
            GOOD, "    if chr(92) in path:\n        raise ValueError(\"不支持反斜杠路径\")\n")
        return (mutated, "路径", [], {"YDFC_TEST_XLSX": "D:/data/a.txt"}) if mutated else None

    def m_docstring_mentions_xbot():
        mutated = GOOD.replace("6. 依赖：只用标准库，无需装包。",
                               "6. 依赖：只用标准库，不依赖 xbot/package，无需装包。", 1)
        return (mutated, "", [], {}) if mutated != GOOD else None

    def m_bom():
        return b"\xef\xbb\xbf" + GOOD.encode("utf-8"), "BOM", [], {}

    def m_two_params():
        mutated = GOOD.replace("def count_lines(path: str, encoding: str = \"utf-8\") -> int:",
                               "def count_lines(path: str, encoding: str) -> int:", 1)
        mutated = mutated.replace('count_lines("C:/data/a.txt")',
                                  'count_lines("C:/data/a.txt", "utf-8")', 1)
        return (mutated, "契约探测", [], {}) if mutated != GOOD else None

    # (用例名, 变异器, 期望结果: fail / pass)
    return [
        ("语法错误", m_syntax, "fail"),
        ("3.11+ 语法", m_py311, "fail"),
        ("3.7 目标下的海象运算符", m_walrus_for_37, "fail"),
        ("骨架：删掉 main", m_no_main, "fail"),
        ("骨架：固定 import 被改", m_import_changed, "fail"),
        ("import 位置错误", m_import_pos, "fail"),
        ("复杂泛型/联合注解", m_generic_ann, "fail"),
        ("函数无 return", m_no_return, "fail"),
        ("docstring 缺项", m_docstring, "fail"),
        ("中文标识符", m_cn_ident, "fail"),
        ("歧义转义", m_escape, "fail"),
        ("Windows 反斜杠路径", m_win_path, "fail"),
        ("默认参数是容器", m_container_default, "fail"),
        ("默认参数含逗号", m_comma_default, "fail"),
        ("代码引用 xbot", m_xbot_use, "fail"),
        ("路径不接受反斜杠", m_path_backslash, "fail"),
        ("UTF-8 BOM", m_bom, "fail"),
        ("docstring 提到 xbot（不该误伤）", m_docstring_mentions_xbot, "pass"),
        ("多必填参数（应 SKIP 而非假通过）", m_two_params, "pass"),
    ]


def run_gate(path, extra_args, extra_env):
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env.update(extra_env)
    cmd = [PY, GATE, path] + list(extra_args)
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
    out = res.stdout.decode("utf-8", "replace")
    err = res.stderr.decode("utf-8", "replace")
    return res.returncode, out + err


def main():
    configure_io()
    if not os.path.isfile(GATE):
        print("找不到门禁脚本:", GATE)
        return 2

    # 可选：先确认调用者自己的模块能过门禁（门禁若冤枉好代码，自检没有意义）
    if len(sys.argv) > 1:
        user_mod = os.path.abspath(sys.argv[1])
        if not os.path.isfile(user_mod):
            print("找不到模块:", user_mod)
            return 2
        code, out = run_gate(user_mod, [], {})
        if code != 0:
            print("你提供的模块未通过门禁，先修模块再看门禁自检：")
            print(out[-3000:])
            return 1
        print("前置检查：%s 通过门禁" % user_mod)

    print("=" * 68)
    print("门禁自检：坏代码必须被抓到，好代码不能被误伤")
    print("=" * 68)

    passed = failed = skipped = 0
    tmp_dir = tempfile.mkdtemp(prefix="ydfc_selftest_")
    try:
        # 样例本身必须过门禁
        good_path = os.path.join(tmp_dir, "good_module.py")
        with open(good_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(GOOD)
        code, out = run_gate(good_path, [], {})
        if code != 0:
            print("  [FAIL] 内置样例模块本身没通过门禁：")
            print(out[-3000:])
            return 1
        print("  [PASS] 内置样例模块通过门禁")

        for name, mutator, expect in build_cases():
            result = mutator()
            if result is None:
                print("  [SKIP] %-26s 变异器不适用于当前样例" % name)
                skipped += 1
                continue
            mutated, keyword, extra_args, extra_env = result
            case_path = os.path.join(tmp_dir, "case.py")
            if isinstance(mutated, bytes):
                with open(case_path, "wb") as fh:
                    fh.write(mutated)
            else:
                if mutated == GOOD and expect == "fail":
                    print("  [FAIL] %-26s 变异没有生效（源码与样例相同）" % name)
                    failed += 1
                    continue
                with open(case_path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write(mutated)

            code, out = run_gate(case_path, extra_args, extra_env)
            has_kw = (keyword in out) if keyword else True
            if expect == "fail":
                ok = code != 0 and has_kw
            else:
                ok = code == 0 and has_kw
            if ok:
                print("  [PASS] %-26s 退出码=%d" % (name, code))
                passed += 1
            else:
                print("  [FAIL] %-26s 退出码=%d 关键词=%s"
                      % (name, code, "命中" if has_kw else "未命中"))
                failed += 1
    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print()
    print("=" * 68)
    if failed:
        print("门禁自检未通过：%d 失败 / %d 通过 / %d 跳过" % (failed, passed, skipped))
        return 1
    print("门禁自检通过  %d 项通过 / %d 项跳过" % (passed, skipped))
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())