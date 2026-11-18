# -*- coding: utf-8 -*-
"""
门禁脚本自身的回归测试（verify_gate.py 的反向测试）。

一个只会报 PASS 的门禁等于没有门禁。本脚本故意造出各类坏代码，
逐个确认 verify_gate.py 能抓到并以非零退出码失败。

用法：
    python verify_gate_selftest.py <一份合格模块的路径>

用法示例（拿自己刚写的模块跑一遍）：
    python verify_gate_selftest.py /tmp/我的模块.py
"""
import ast
import os
import re
import subprocess
import sys

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.join(HERE, "verify_gate.py")


def build_cases(good):
    """每项：(用例名, 变异函数, 期望门禁输出里出现的关键词)

    注意：每个用例必须"只坏一处"。若变异本身就产生了语法错误，
    那测到的是 ast.parse 而不是目标检查项——所以用例会先 ast.parse 自检。
    """

    def m_syntax(s):
        # 只坏语法，且只在一个可控位置
        return s.replace("    return result", "    return result)", 1)

    def m_import_pos(s):
        return s + "\nimport json\n"

    def m_generic_ann(s):
        return s.replace("-> dict:", "-> dict[str, float] | None:", 1)

    def m_no_return(s):
        # 删掉函数体里所有带返回值的 return（含嵌套块内的），
        # 但保留内嵌 def 内部的 return —— 那样才测的是"外层忘了 return"。
        out, in_nested = [], 0
        for line in s.splitlines():
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())
            if stripped.startswith("def ") or stripped.startswith("class "):
                in_nested += 1
            if in_nested and stripped.startswith("return ") and indent > 4:
                # 内嵌函数的 return 不动
                out.append(line)
                continue
            if stripped.startswith("return ") and "return value" not in stripped:
                out.append(" " * indent + "pass")
                continue
            out.append(line)
            if in_nested and stripped == "" :
                pass
        # 修正：内嵌函数体结束后要退出计数，用缩进判断更稳，这里重做一遍
        return "\n".join(out) + "\n"

    def _strip_own_returns(source):
        """删除顶层新函数体内所有 return（不含内嵌 def 的）"""
        tree = ast.parse(source)
        target = None
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name != "main":
                target = node
        if target is None:
            return source
        nested_ids = set()
        for node in ast.walk(target):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node is not target:
                for sub in ast.walk(node):
                    nested_ids.add(id(sub))
        lines = source.splitlines()
        for node in ast.walk(target):
            if isinstance(node, ast.Return) and node.value is not None and id(node) not in nested_ids:
                ln = node.lineno - 1
                indent = len(lines[ln]) - len(lines[ln].lstrip())
                lines[ln] = " " * indent + "pass"
        return "\n".join(lines) + "\n"

    m_no_return = _strip_own_returns

    def m_docstring(s):
        return re.sub(r"^\s*6\. .*\n", "", s, count=1, flags=re.M)

    def m_cn_ident(s):
        return re.sub(r"def (\w+)\(", lambda mo: "def 提取%s(" % mo.group(1), s, count=1)

    def m_raw_escape(s):
        # 造一个含 \U 转义的普通字符串（非 raw）。这里用单引号写 Python 源码，
        # 使文件里落到的是真正的反斜杠 + U。
        inject = "    Y = " + repr("C:\\Users\\admin") + "\n"
        return s.replace("    r\"\"\"", '    """' + "\n" + inject, 1)

    def m_win_path(s):
        inject = "    Z = " + repr("C:\\Users\\admin\\x.xlsx") + "\n"
        return s.replace("    r\"\"\"", '    """' + "\n" + inject, 1)

    def m_container_default(s):
        return re.sub(r"def (\w+)\(([^)]*?)\):",
                      lambda mo: "def %s(%s, extra: list = []):" % (mo.group(1), mo.group(2)),
                      s, count=1)

    def m_xbot_use(s):
        # 在函数体内第一行插一行 xbot 调用，保持缩进合法
        return re.sub(r"^(def \w+\(.*?\n(?:.*?\n)*?)(    )",
                      lambda mo: mo.group(1) + "    xbot_marker = 1\n" + mo.group(2),
                      s, count=1, flags=re.M)

    return [
        ("语法错误", m_syntax, "ast.parse"),
        ("3.11+ 语法", lambda s: s + "\n\ndef _probe(v):\n    match v:\n        case 1:\n            return 1\n    return 0\n", "3.10"),
        ("骨架：删掉 main", lambda s: s.replace("def main(args):\n    pass", "# main 没了"), "main"),
        ("骨架：固定 import 被改", lambda s: s.replace("from xbot import print, sleep", "from xbot import print"), "固定 import"),
        ("import 位置错误", m_import_pos, "位置 A"),
        ("复杂泛型注解", m_generic_ann, "复杂泛型"),
        ("函数无 return", m_no_return, "return"),
        ("docstring 缺项", m_docstring, "docstring 八项"),
        ("中文标识符", m_cn_ident, "ASCII"),
        ("裸歧义转义", m_raw_escape, "ast.parse"),
        ("Windows 反斜杠路径", m_win_path, "反斜杠路径"),
        ("默认参数是容器", m_container_default, "默认参数"),
        ("引用 xbot", m_xbot_use, "xbot"),
    ]


# 这些用例本身就是"语法坏"的，不该被用例自检拦下——它们要测的正是语法检查。
MAY_BE_SYNTAX_BAD = {"语法错误", "裸歧义转义"}


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    good_path = os.path.abspath(sys.argv[1])
    if not os.path.isfile(good_path):
        print("找不到文件:", good_path)
        return 2
    good = open(good_path, encoding="utf-8").read()
    if "def main(args):" not in good:
        print("这不是影刀模块（缺少 def main(args)）")
        return 2

    tmp = os.path.join(os.path.dirname(good_path), "_ydfc_selftest_case.py")
    passed = failed = 0
    print("=" * 68)
    print("门禁自检：坏代码必须被抓到")
    print("=" * 68)
    for name, mutate, keyword in build_cases(good):
        try:
            src = mutate(good)
            # 用例本身必须是合法语法，否则测的是别的东西。
            # 但"语法错误"类用例本身就是坏的，豁免。
            if name not in MAY_BE_SYNTAX_BAD:
                ast.parse(src)
        except SyntaxError as e:
            print("  [SKIP] %-22s 用例构造本身有语法错：%s" % (name, e.msg))
            failed += 1
            continue
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src)
        res = subprocess.run([PY, GATE, tmp], capture_output=True, text=True, encoding="utf-8")
        out = res.stdout + res.stderr
        caught = res.returncode != 0
        has_kw = keyword in out
        if caught and has_kw:
            print("  [PASS] %-22s 退出码=%d" % (name, res.returncode))
            passed += 1
        else:
            print("  [FAIL] %-22s 退出码=%d 关键词命中=%s" % (name, res.returncode, has_kw))
            failed += 1
    try:
        os.remove(tmp)
    except OSError:
        pass

    print()
    print("=" * 68)
    if failed:
        print("门禁自检未通过：%d 项失败 / %d 项通过" % (failed, passed))
        return 1
    print("门禁自检通过 ✅  %d/%d 类坏代码都能被抓到" % (passed, passed))
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(main())
