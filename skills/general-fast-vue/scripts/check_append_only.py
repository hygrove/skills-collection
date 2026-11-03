#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验「事实表只增不减」铁律（架构手册 §3.4 🔴）。

为什么需要这个闸门：
    「只增不减」防的是**僵尸行**——源表被移走/归档后，对应行冻结在事实表里，
    仍在参与聚合、永不更新、零报错。症状是页面上的数字莫名其妙对不上，
    但没有任何错误提示，是最危险的静默损坏。

    为什么不能简单地「全项目禁止 DELETE」：
        项目里本来就有需要删除的场景——
          · 摄入层的「整表重算」需要先清掉旧行再写入；
          · **按键重算**（DELETE WHERE key=… 后立刻 INSERT OR REPLACE 写回）
            ——语义仍是 upsert，不是「把事实表当可写业务表」；
          · 保留策略（retention）按周期淘汰过期快照——手册明确说这类删除合法；
          · 辅助表（已处理文件清单、映射表）随源文件变化而清理；
          · 校验脚本的夹具（造数据用），不是业务代码。
        这些都是**该删的**。一刀切禁止 DELETE 会让闸门失去意义、
        最终被人加豁免绕过——那才是真正的失败。

    本脚本的判定规则（两条同时满足才算违规）：
        ① 目标是**事实表**（宽表、明细、日级/流水语义）；
        ② 语句是 **DELETE 或 UPDATE**，且**带行级条件**（WHERE 子句非空）。

    判定为**违规**的语义 = 「事实表被当成可写业务表」：
        用户改了数据 → 直接 UPDATE 事实表；或 DELETE 某一行且不补回。
        这会让源文件重跑时把用户的修改冲掉，或让行冻结成僵尸行。

    判定为**合法**的（不报）：
        · 整表重算（DELETE FROM t 无 WHERE）；
        · 按键重算（DELETE ... WHERE key 之后紧跟 INSERT OR REPLACE 写回）；
        · 保留策略淘汰（retention 模块内）；
        · 辅助表（表名不含事实表特征词）；
        · UPSERT 本身（INSERT OR REPLACE / ON CONFLICT）。

    怎么声明哪些是事实表：
        自动识别（表名含 daily/detail/fact/record/raw/entry/line_item 等特征词）；
        或用 `--fact-table` 显式指定（可重复）——**显式指定优先级更高**，
        特征词识别会有误判，用它来排除「像事实表但允许删改」的表。

用法：
    python check_append_only.py <后端目录> [--fact-table 表名]...
    例：python check_append_only.py <项目>/backend
    例：python check_append_only.py ./backend --fact-table daily_detail --fact-table orders

退出码：0 = 通过；1 = 发现事实表被逐行删改。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# 事实表特征词：宽表 / 明细 / 日级 / 流水 语义。
# ⚠️ 刻意不用 metric / data 这类泛词——派生指标表、维度表也算事实表。
#
# ⚠️ 中英文都要覆盖：中文项目里表名常是「巡检记录」「日度明细」这类词，
#    只匹配英文会导致事实表完全漏检（闸门输出 PASS 而实际失明）。
FACT_TABLE_PATTERNS = [
    # 英文
    r"daily", r"detail", r"_fact", r"^fact", r"fact_",
    r"record", r"_record", r"records",
    r"raw", r"_raw", r"entry", r"_entry",
    r"line_item", r"lineitem",
    # 中文（宽表 / 明细 / 日级 / 流水 / 记录 / 事实 / 原始）
    # ⚠️ 「记录」单独出现即算特征词：中文表名常以「XX记录」结尾（巡检记录、日志记录）。
    r"明细", r"流水", r"日[度级]", r"事实", r"原始", r"记录", r"台账",
    r"快照", r"数据表",
]

# DELETE / UPDATE 语句（排除 INSERT OR REPLACE —— 那是 upsert，不是删改）
#
# ⚠️ 表名部分必须同时支持 ASCII 与中文：中文项目的表名常是「巡检记录」「日度明细」
#    这类词，只认 [A-Za-z_] 会让中文表名的违规语句完全漏检。
_IDENT = r"[A-Za-z_一-鿿][A-Za-z0-9_一-鿿]*"
DELETE_RE = re.compile(rf"\bDELETE\s+FROM\s+({_IDENT})", re.IGNORECASE)
UPDATE_RE = re.compile(rf"\bUPDATE\s+({_IDENT})\s+SET\b", re.IGNORECASE)

# WHERE 子句检测：语句中 DELETE/UPDATE 之后是否出现 WHERE
WHERE_RE = re.compile(r"\bWHERE\b", re.IGNORECASE)

# SQL 字符串字面量（只扫字符串里的 SQL，避开 Python 代码里的其他文本）
SQL_STRING_RE = re.compile(r"""(?:f|r|rf|fr)?["']([^"']*(?:SELECT|UPDATE|DELETE|INSERT)[^"']*)["']""", re.IGNORECASE)

# 按键重算的识别：DELETE ... WHERE <key> 之后（含同一语句或紧邻语句）
# 出现对该表的 INSERT OR REPLACE —— 语义是 upsert（先删后写回），不是「把事实表当可写表」。
UPSERT_RE = re.compile(rf"\bINSERT\s+OR\s+REPLACE\s+INTO\s+({_IDENT})", re.IGNORECASE)

# 保留策略模块：按周期淘汰过期快照是**手册明确认可的合法删除**。
# 识别方式：路径里含 retention / expire / cleanup / purge 等词。
RETENTION_PATH_RE = re.compile(r"retention|expire|cleanup|purge|淘汰|保留策略", re.IGNORECASE)

# 校验脚本 / 一次性工具：它们造夹具数据时会删改任意表——那是测试行为，不是业务行为。
# 与 check_no_bare_print.py 的豁免口径保持一致。
EXEMPT_FILE_PREFIXES = ("verify_", "check_", "setup_", "conftest_", "test_")
EXEMPT_DIR_NAMES = {"tests", "test", "scripts"}


def is_fact_table(table: str, explicit: set[str]) -> bool:
    """表是否应按「事实表」规则检查。"""
    low = table.lower()
    if low in explicit:
        return True
    return any(re.search(p, low) for p in FACT_TABLE_PATTERNS)


def scan(root: Path, explicit: set[str], exempt_tables: set[str]) -> list[tuple[str, int, str, str]]:
    """返回 (文件, 行号, 语句类型, 表名) 列表。

    判定要点（三条豁免）：
      ① 保留策略模块（路径含 retention/expire/cleanup/purge）→ 整文件豁免；
      ② 按键重算：DELETE 之后（同一语句或后续 3 行内）出现对该表的 INSERT OR REPLACE → 豁免；
      ③ 显式豁免表（--exempt-table）→ 豁免。
    """
    hits: list[tuple[str, int, str, str]] = []

    if root.is_file():
        targets = [root]
    else:
        targets = [
            p for p in root.rglob("*.py")
            if "__pycache__" not in str(p) and ".venv" not in str(p)
        ]

    for f in targets:
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        # ① 保留策略模块整文件豁免
        if RETENTION_PATH_RE.search(str(f).replace("\\", "/")):
            continue

        # ①' 校验脚本 / 测试目录 / 一次性工具豁免（造夹具数据是测试行为）
        if f.name.startswith(EXEMPT_FILE_PREFIXES):
            continue
        if any(part in EXEMPT_DIR_NAMES for part in f.parts):
            continue

        # 收集本文件里所有 upsert 目标表与其行号，供「按键重算」判断
        upsert_targets: dict[str, list[int]] = {}
        for idx, line in enumerate(lines, start=1):
            for um in UPSERT_RE.finditer(line):
                upsert_targets.setdefault(um.group(1).lower(), []).append(idx)

        for idx, line in enumerate(lines, start=1):
            # 只看字符串字面量里的 SQL
            for m in SQL_STRING_RE.finditer(line):
                sql = m.group(1)
                upper = sql.upper()
                # 排除 upsert 本身
                if "INSERT" in upper and ("OR REPLACE" in upper or "ON CONFLICT" in upper):
                    continue
                for kind, rx in (("DELETE", DELETE_RE), ("UPDATE", UPDATE_RE)):
                    for tm in rx.finditer(sql):
                        table = tm.group(1)
                        low = table.lower()
                        if low in exempt_tables:
                            continue
                        if not is_fact_table(table, explicit):
                            continue
                        # 只看带 WHERE 的逐行删改；整表重建（无 WHERE）合法
                        tail = sql[tm.end():]
                        if not WHERE_RE.search(tail):
                            continue
                        # ② 按键重算豁免：紧邻几行内出现对该表的 INSERT OR REPLACE
                        if low in upsert_targets:
                            near = [ln for ln in upsert_targets[low] if 0 <= ln - idx <= 3]
                            if near:
                                continue
                        hits.append((str(f), idx, kind, table))

    return hits


def main() -> int:
    args = sys.argv[1:]
    positional: list[str] = []
    explicit: set[str] = set()
    exempt: set[str] = set()
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--fact-table":
            if i + 1 >= len(args):
                print("[FAIL] --fact-table 需要一个表名")
                return 2
            explicit.add(args[i + 1].lower())
            i += 2
            continue
        if a.startswith("--fact-table="):
            explicit.add(a.split("=", 1)[1].lower())
            i += 1
            continue
        if a == "--exempt-table":
            if i + 1 >= len(args):
                print("[FAIL] --exempt-table 需要一个表名")
                return 2
            exempt.add(args[i + 1].lower())
            i += 2
            continue
        if a.startswith("--exempt-table="):
            exempt.add(a.split("=", 1)[1].lower())
            i += 1
            continue
        if a.startswith("--"):
            i += 1
            continue
        positional.append(a)
        i += 1

    if len(positional) < 1:
        print("用法: python check_append_only.py <后端目录> [--fact-table 表名]... [--exempt-table 表名]...")
        print("例:   python check_append_only.py ./backend --fact-table daily_detail")
        print()
        print("  判定：事实表上出现带 WHERE 的 DELETE / UPDATE，且不是按键重算，即违规。")
        print("  合法：整表重算（无 WHERE）、按键重算（DELETE 后写回）、保留策略淘汰、辅助表清理、UPSERT。")
        print()
        print("  --fact-table   显式声明事实表（优先于特征词自动识别）")
        print("  --exempt-table 显式豁免某表（它像事实表但允许逐行删改）")
        return 2

    root = Path(positional[0])
    if not root.exists():
        print(f"[FAIL] 路径不存在: {root}")
        return 1

    hits = scan(root, explicit, exempt)

    if not hits:
        print("[PASS] 事实表未被逐行删改（手册 §3.4：只增不减，防僵尸行）")
        print("       （整表重算、按键重算、保留策略淘汰、辅助表清理均不违规）")
        return 0

    print(f"[FAIL] 发现 {len(hits)} 处对事实表的逐行删改：")
    for f, line_no, kind, table in hits:
        print(f"  {f}:{line_no}  {kind} 表 {table!r}")
    print()
    print("  为什么这是致命项：事实表被当成可写业务表后——")
    print("    · 源文件重跑会冲掉用户的修改（静默丢数据）；")
    print("    · 源表被移走/归档后，对应行冻结成僵尸行：仍在聚合、永不更新、零报错。")
    print()
    print("  修法（四选一）：")
    print("    ① 逐行修正走独立的修正层（override 表），查询时叠加，不动事实表 ← 推荐")
    print("    ② 该表本就该可写 → 用 --exempt-table 显式豁免，并写 ADR 说明它为何不是事实表")
    print("    ③ 改成按键重算（DELETE 后 INSERT OR REPLACE 写回）")
    print("    ④ 整表重算（去掉行级 WHERE）")
    return 1


if __name__ == "__main__":
    sys.exit(main())
