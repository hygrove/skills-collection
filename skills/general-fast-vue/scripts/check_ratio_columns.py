#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验「长表只存可累加原始列，比率指标不入库」铁律（架构手册 §3.2 🔴）。

为什么需要这个闸门：
    比率（转化率、均价、投入产出比、占比…）一旦写进事实表，
    跨期 / 跨维度 / 跨区间汇总时就会出错——把比率相加或取平均，
    与「先按维度求和、再相除」的真实口径不一致。
    例：两天各 10%、20%，区间真实值是 15%，简单平均只是**恰好**巧合对。
    一旦错了，图表看起来完全正常，只有对照原始数据才发现——静默的统计错误。

    判定方式：扫描事实表的建表语句（CREATE TABLE）与列定义，
    若列名命中比率类模式（rate / ratio / percent / pct / avg / average / 占比…），
    即判为违规。

    ⚠️ 豁免（两个条件**同时**成立才豁免）：
    1. 列名包含 `_ratio_` 标记（如 `_ratio_derived`、`sales_ratio_final`）——
       作者声明「这列是派生指标」；
    2. **且** 它所在的表不是事实表。事实表按表名特征词判定：
       daily / detail / fact / record / raw / entry / line_item 等。
       ⚠️ 刻意**不含** metric / data 这类泛词——派生指标表常叫
       `derived_metrics` / `metrics_daily`，用泛词会把它们误判成事实表，
       豁免就永远不生效，闸门退化成「凡是比率列一律拦下」。
    ⚠️ 两个条件缺一即判违规：只在列名上加标记等于给事实表开了万能钥匙——
       `daily_conversion_ratio_derived` 恰恰是最该拦下的名字。
    ⚠️ 另：SQLite 系统表（sqlite_sequence 等）无条件豁免。

用法：
    python check_ratio_columns.py <项目根目录或后端目录>
    例：python check_ratio_columns.py <项目>/backend

退出码：0 = 通过；1 = 发现疑似比率列。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# 比率类列名模式：命中即视为疑似派生指标。
#
# ⚠️ 中英文都要覆盖：中文项目里列名常是「得分率」「合格率」「转化率」「客单价」
#    这类词，只匹配英文会让比率列完全漏检（闸门输出 PASS 而实际失明）。
RATIO_PATTERNS = [
    # 英文
    r"_rate$", r"_rate_", r"^rate_", r"_ratio$", r"_ratio_", r"^ratio_",
    r"_percent$", r"_percent_", r"^percent_", r"_pct$", r"_pct_", r"^pct_",
    r"_avg$", r"_avg_", r"^avg_", r"_average$", r"_average_",
    r"_ratio\b", r"\bratio_",
    r"_share$", r"_share_", r"^share_",       # 占比
    r"_conversion$", r"_conversion_",          # 转化率
    r"_roi$", r"_roi_", r"^roi_",              # 投入产出比
    r"_margin$", r"_margin_", r"^margin_",    # 毛利率
    # 中文：率 / 占比 / 均值 / 单价 / 倍数（比率或派生值）
    r"率$", r"占比", r"均值", r"平均", r"单价", r"倍数", r"比例",
]

# CREATE TABLE 语句的捕获
CREATE_TABLE_RE = re.compile(
    r"""CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?["'`]?([^\W\d_][\w]*)["`]?\s*\(([^;]*?)\)\s*;""",
    re.IGNORECASE | re.DOTALL,
)

# 单列定义：列名 + 类型 + 约束
COLUMN_RE = re.compile(
    r"""^\s*["'`]?([^\W\d_][\w]*)["'`]?\s+([A-Za-z][A-Za-z0-9_]*(?:\s*\([^)]*\))?)""",
    re.IGNORECASE,
)

# 明确的非列名 token（约束关键字、类型名等）
NON_COLUMN = {
    "primary", "foreign", "unique", "check", "constraint", "not", "null",
    "default", "references", "autoincrement", "integer", "text", "real",
    "numeric", "blob", "boolean", "date", "datetime", "timestamp", "varchar",
    "char", "float", "double", "decimal", "bigint", "smallint", "json",
    "jsonb", "uuid", "serial", "bigserial",
}

# 系统表 / 明确豁免
EXEMPT_TABLES = {"sqlite_sequence", "sqlite_stat1", "sqlite_stat4"}

# 事实表判定：这些表名是「可累加事实表」的常见命名。
# 只有事实表才受「比率不入库」铁律约束——派生指标表（单独存放比率的表）不在此列。
#
# ⚠️ 关键词要窄，不能用 `metric` / `data` 这类泛词：
#   派生指标表常叫 `derived_metrics` / `metrics_daily`，用泛词会把它们
#   误判成事实表 → 豁免永不生效 → 闸门变成「凡是比率列一律拦下」，
#   那就没有豁免机制了。下面的词都指向「明细/流水/原始记录」这一语义。
FACT_TABLE_PATTERNS = [
    r"daily",      # daily_detail / daily_metric
    r"detail",     # sales_detail
    r"_fact", r"^fact", r"fact_",   # fact_sales
    r"record", r"_record", r"records",
    r"raw", r"_raw",
    r"entry", r"_entry",
    r"line_item", r"lineitem",
]

# 派生指标显式标记：列名中**包含**该标记即视为「作者声明这是派生指标」。
#
# ⚠️ 为什么不能只看列名就放行（这是踩过的坑）：
#   只看列名 = 万能钥匙。`daily_conversion_ratio_derived` 这类列会同时
#   命中「它是派生比率」与「它有 _ratio_ 标记」两个信号，一并放行——
#   而它恰恰是最该拦下的名字（存的是每天算好的转化率，汇总时必错）。
#
#   故豁免需**两个条件同时成立**：
#     ① 列名带 _ratio_ 标记（作者声明它是派生指标）；
#     ② 它所在的**不是事实表**（派生指标表可以合法存比率）。
#   两条缺一即判违规。
DERIVED_MARKER = "_ratio_"


def is_fact_table(table: str) -> bool:
    """表名是否像事实表（受「比率不入库」铁律约束）。"""
    low = table.lower()
    return any(re.search(p, low) for p in FACT_TABLE_PATTERNS)


def is_exempt_column(name: str, table: str) -> bool:
    """列是否豁免：带派生标记 **且** 所在表不是事实表。"""
    if DERIVED_MARKER not in name.lower():
        return False
    return not is_fact_table(table)


def looks_like_ratio(name: str) -> bool:
    """判断列名是否像比率类指标（不含豁免判断）。"""
    low = name.lower()
    for pat in RATIO_PATTERNS:
        if re.search(pat, low):
            return True
    return False


def scan(root: Path) -> list[tuple[str, str, str]]:
    """返回 (表名, 列名, 文件) 三元组列表。"""
    hits: list[tuple[str, str, str]] = []

    if root.is_file():
        targets = [root]
    else:
        targets = [
            p for p in root.rglob("*.py")
            if "__pycache__" not in str(p) and ".venv" not in str(p)
        ]

    for f in targets:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        for m in CREATE_TABLE_RE.finditer(text):
            table = m.group(1)
            if table.lower() in EXEMPT_TABLES:
                continue
            body = m.group(2)
            # 按逗号拆列定义（忽略括号内的逗号，如 DECIMAL(10,2)）
            depth = 0
            buf = ""
            cols: list[str] = []
            for ch in body:
                if ch == "(":
                    depth += 1
                elif ch == ")":
                    depth -= 1
                if ch == "," and depth == 0:
                    cols.append(buf)
                    buf = ""
                else:
                    buf += ch
            cols.append(buf)

            for col_def in cols:
                cm = COLUMN_RE.match(col_def)
                if not cm:
                    continue
                col_name = cm.group(1)
                if col_name.lower() in NON_COLUMN:
                    continue
                # 豁免需同时满足：带派生标记 **且** 所在表不是事实表
                if is_exempt_column(col_name, table):
                    continue
                if looks_like_ratio(col_name):
                    hits.append((table, col_name, str(f)))

    return hits


def main() -> int:
    if len(sys.argv) < 2:
        print("用法: python check_ratio_columns.py <项目根目录或后端目录>")
        print("例:   python check_ratio_columns.py <项目>/backend")
        return 2

    root = Path(sys.argv[1])
    if not root.exists():
        print(f"[FAIL] 路径不存在: {root}")
        return 1

    hits = scan(root)

    if not hits:
        print("[PASS] 事实表未发现比率类列（手册 §3.2：比率查询时算，不入库）")
        print("       （比率入库会在跨期/跨维度汇总时静默算错：两天 10%、20% → 真实 15%，平均只是巧合）")
        return 0

    print(f"[FAIL] 发现 {len(hits)} 个疑似比率列写入事实表：")
    for table, col, f in hits:
        print(f"  {f}")
        print(f"    表 {table} 的列 {col!r}")
    print()
    print("  修法：把该列从建表语句移除，改为查询时「先按维度求和、再相除」。")
    print("  若它确实是必须存的原始计数，请改名以避开比率语义（如 xxx_count / xxx_amount）。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
