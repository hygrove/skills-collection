#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验「后端不用裸 print，用 logging」铁律（可观测性下限）。

为什么需要这个闸门：
    print() 写到 stdout。而项目若以**无控制台**方式启动
    （Windows 下 pythonw.exe + CREATE_NO_WINDOW，常见于「双击即用」的托盘模式），
    则 sys.stdout 为 None —— 此时 print() **不报错，但静默丢弃**：
    后端所有诊断信息一行都落不了盘，故障排查时毫无线索。

    同时 print 缺少三个必需能力：
      - 级别（无法只筛 ERROR）；
      - 异常堆栈（except 里 print(str(e)) 只剩一行文字，定位不到代码行）；
      - 结构化字段（无法 grep 解析、无法关联一次请求的多层调用）。

    本脚本在**应用代码**中检出裸 print。豁免：
      - 校验脚本 / 一次性脚本（verify_*.py、scripts/ 下的 CLI 工具）——
        它们的 print 是**给人看的正常输出**，不是日志；
      - 注释与文档字符串里的 print 字样。

用法：
    python check_no_bare_print.py <后端目录>
    例：python check_no_bare_print.py <项目>/backend

退出码：0 = 通过；1 = 发现疑似裸 print。
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

# 文件名豁免：这些是 CLI 校验脚本 / 一次性工具，print 是其正常输出。
# ⚠️ 只匹配**文件名**（如 verify_organize.py），不匹配整条路径——
#    按路径子串匹配会让业务目录名含 "check_" 时（如 check_orders/）
#    整目录失明，那正是最不该漏的地方。
EXEMPT_FILE_PREFIXES = ("verify_", "check_", "setup_")

# 目录豁免：按**路径段**匹配，且只匹配目录名本身。
EXEMPT_DIR_NAMES = {"scripts"}


def has_exempt_path(path: Path) -> bool:
    """路径是否属于豁免范围。

    规则：
      ① 文件名以 verify_ / check_ / setup_ 开头 → 豁免；
      ② 路径中存在名为 scripts 的目录段 → 豁免。
    业务目录名偶然含 "check_" 不会被误伤（那不是独立路径段且不是文件名前缀）。
    """
    if path.name.startswith(EXEMPT_FILE_PREFIXES):
        return True
    return any(part in EXEMPT_DIR_NAMES for part in path.parts)


def scan_file(path: Path) -> list[tuple[int, str]]:
    """返回该文件中的 (行号, 代码片段) 列表。"""
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (OSError, UnicodeDecodeError, SyntaxError):
        return []

    hits: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # print(...)  —— 内置函数
        if isinstance(func, ast.Name) and func.id == "print":
            hits.append((node.lineno, "print(...)"))
        # sys.stdout.write(...) / print(..., file=sys.stdout)
        elif isinstance(func, ast.Attribute) and func.attr == "write":
            if isinstance(func.value, ast.Attribute) and func.value.attr == "stdout":
                hits.append((node.lineno, "sys.stdout.write(...)"))
    return hits


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python check_no_bare_print.py <后端目录>")
        print("例:   python check_no_bare_print.py <项目>/backend")
        return 2

    root = Path(sys.argv[1])
    if not root.exists():
        print(f"[FAIL] 路径不存在: {root}")
        return 1

    files = [root] if root.is_file() else [
        p for p in root.rglob("*.py")
        if "__pycache__" not in str(p) and ".venv" not in str(p)
    ]

    all_hits: list[tuple[Path, int, str]] = []
    for f in files:
        if has_exempt_path(f):
            continue
        for line_no, kind in scan_file(f):
            all_hits.append((f, line_no, kind))

    if not all_hits:
        print("[PASS] 后端应用代码未使用裸 print（可观测性下限达标）")
        print("       （无控制台环境下 print 会静默丢弃；且它没有级别、没有堆栈、无法结构化检索）")
        return 0

    print(f"[FAIL] 发现 {len(all_hits)} 处裸 print / sys.stdout.write：")
    for f, line_no, kind in all_hits:
        print(f"  {f}:{line_no}  {kind}")
    print()
    print("  修法：用 logging.getLogger(__name__).info(...) 代替 print。")
    print("  在 except 块内改用 logger.exception(...) —— 它自动带上异常堆栈，")
    print("  而 print(str(e)) 只留一行文字，定位不到代码行。")
    print()
    print("  豁免范围：verify_*/check_*/setup_* 与 scripts/ 下的 CLI 脚本")
    print("  （它们的 print 是给人看的正常输出，不是日志）。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
