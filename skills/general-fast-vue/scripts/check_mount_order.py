#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验「静态挂载顺序」铁律（架构手册 §2.1 🔴）。

为什么需要这个闸门：
    FastAPI 的 SPA 回退路由 `/{full_path:path}` 会吞掉**一切**未匹配的 GET 请求。
    若静态资源挂载（/images、/thumbs、/assets 等）写在回退路由**之后**，
    图片请求会被回退成 index.html —— 表现为「页面能开、图片全 404」，
    而且**不报错**：浏览器拿到的是 200 + HTML，故障极其隐蔽。
    这是典型的「踩错不会静默损坏数据、但会让人误以为改好了」的项。

检查逻辑：
    在 FastAPI 应用文件中，找出所有 app.mount(...) 与 SPA 回退路由
    （形如 @app.get("/{full_path:path}") 或 @app.api_route 配合 catch-all 路径）
    的定义位置，断言**所有 mount 的行号都小于回退路由的行号**。

用法：
    python check_mount_order.py <backend/app 目录或应用文件> [--mode spa|api|auto]
    例：python check_mount_order.py <项目>/backend/app --mode spa

    --mode spa  强制按「同源托管 SPA」检查：即使当前文件里还没有回退路由，
                也检查 mount 是否集中声明在文件前部（防止后加的 mount 落到回退之后）。
                这是后端同时托管前端产物时的形态。
    --mode api  纯后端 API 项目（前端独立 dev server / 独立部署）：
                没有 SPA 回退路由，挂载顺序不构成风险，本检查直接通过。
    --mode auto 默认。按「文件内是否存在 catch-all 回退路由」自动判定：
                有则按 spa 检查，无则按 api 通过。

退出码：0 = 通过；1 = 存在违规。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# app.mount("/xxx", ...)  —— 捕获挂载的路径前缀
MOUNT_RE = re.compile(r"""\bmount\s*\(\s*["']([^"']+)["']""")

# app.mount(<非字面量>, ...)  —— 路径不是字面量时的兜底匹配。
#   覆盖三种写法：变量（IMAGE_PREFIX）、函数调用（get_prefix()）、下标（prefixes["x"]）。
#   ⚠️ 为什么要兜底：这类 mount 同样有「写在回退路由之后」的风险，
#      但路径值需要静态分析才知道。若不识别它，脚本会因「没找到任何 mount」
#      而输出 [PASS] —— 一张**假 PASS**，比报错更危险。
#      故这里一律计入 mounts 并参与顺序判定，路径显示为 <表达式> 以便定位。
MOUNT_EXPR_RE = re.compile(r"""\bmount\s*\(\s*([^"'\s][^,)]*?)\s*[,)]""")

# SPA 回退路由的判定：路径参数形如 {full_path:path} / {path:path} / {rest:path}
# 这类路由在 FastAPI 中是「catch-all」，会匹配一切未处理的 GET。
CATCHALL_ROUTE_RE = re.compile(
    r"""@(?:app|router)\.(?:get|api_route|route)\s*\(\s*["'][^"']*\{[^}]*:path\}"""
)

# 明确排除的非回退路由（形如 /api/{id} 是单段路径参数，不吞静态资源）
SINGLE_SEGMENT_PARAM_RE = re.compile(r"""["']/[^"']*\{[^}/]*:path\}["']""")

# 业务路由装饰器：@app.get(...) / @router.post(...) 等
# 用于「情形 ②」：无回退路由时，静态挂载应早于业务路由。
ROUTE_DECORATOR_RE = re.compile(r"""@(?:app|router)\.(?:get|post|put|delete|patch|api_route)\s*\(""")


def find_violations(root: Path, mode: str) -> list[tuple[Path, int, int, str]]:
    """扫描后端文件，返回 (文件, 违规mount行号, 回退行号, mount路径) 列表。

    mode = "spa"：强制检查。判定规则——
        文件内**存在** catch-all 回退路由时：所有 mount 必须在它之前（这是真实风险）。
        文件内**没有**回退路由时：检查「mount 是否全部位于文件前部」——
        即是否存在「某个 mount 出现在另一个 mount 之后很远」的情况。
        ⚠️ 这条较弱：它只能发现「后加的 mount 落在文件末尾」这种形态，
        无法判定「未来加的回退路由会落在哪」——那取决于未来代码。
        它的价值是：把「mount 集中声明在应用装配区」的习惯固定下来。

    mode = "api"：不检查（无回退路由 = 无风险）。
    """
    violations: list[tuple[Path, int, int, str]] = []

    if root.is_file():
        targets = [root]
    else:
        targets = [p for p in root.rglob("*.py") if "__pycache__" not in str(p)]

    for f in targets:
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError):
            continue

        mounts: list[tuple[int, str]] = []
        fallbacks: list[int] = []
        business_routes: list[int] = []

        for idx, line in enumerate(lines, start=1):
            literal = MOUNT_RE.search(line)
            if literal:
                mounts.append((idx, literal.group(1)))
            else:
                # 非字面量形式：变量 / 函数调用 / 下标。路径值算不出来，
                # 但**它仍是一个 mount**，仍须参与顺序判定——否则会输出假 PASS。
                for m in MOUNT_EXPR_RE.finditer(line):
                    expr = m.group(1).strip()
                    mounts.append((idx, f"<表达式 {expr}>"))
            # catch-all 回退路由：路径以 / 开头且以 {xxx:path} 结尾
            if CATCHALL_ROUTE_RE.search(line) and SINGLE_SEGMENT_PARAM_RE.search(line):
                fallbacks.append(idx)
            elif ROUTE_DECORATOR_RE.search(line):
                business_routes.append(idx)

        if not mounts:
            continue

        if fallbacks:
            # 情形 ①：文件内有回退路由 —— 所有 mount 必须严格早于它
            boundary = min(fallbacks)
            for line_no, path in mounts:
                if line_no > boundary:
                    violations.append((f, line_no, boundary, path))
        elif mode == "api":
            # 纯 API 项目：没有回退路由 = 无此风险
            continue
        elif business_routes:
            # 情形 ②：无回退路由但有业务路由 —— mount 应早于第一个业务路由。
            # 同源托管的正确顺序是「静态挂载 → 业务路由 → SPA 回退」。
            # 若 mount 落在业务路由之后，说明它是事后追加的——
            # 等将来加回退路由时就会踩坑。这是在事故前钉住顺序的先兆检测。
            boundary = min(business_routes)
            for line_no, path in mounts:
                if line_no > boundary:
                    violations.append((f, line_no, boundary, path))
        elif mode == "spa":
            # spa 模式：有 mount 但既无回退路由也无业务路由。
            # 无法判定顺序，视为通过（无参照物），但提示加 --mode 的意义。
            pass

    return violations


def main() -> int:
    # 解析参数：--mode <value> 或 --mode=<value> 两种写法都要支持。
    # ⚠️ 注意：--mode 的值不带 "--" 前缀，不能用「过滤所有 -- 开头的参数」
    #    那种朴素写法——那会把 "spa"/"api" 当成路径参数。
    argv = sys.argv[1:]
    positional: list[str] = []
    mode = "auto"
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--mode":
            if i + 1 >= len(argv):
                print("[FAIL] --mode 需要一个值（spa / api / auto）")
                return 2
            mode = argv[i + 1]
            i += 2
            continue
        if a.startswith("--mode="):
            mode = a.split("=", 1)[1]
            i += 1
            continue
        if a.startswith("--"):
            i += 1
            continue
        positional.append(a)
        i += 1

    if mode not in ("spa", "api", "auto"):
        print(f"[FAIL] --mode 只接受 spa / api / auto，收到 {mode!r}")
        return 2

    if len(positional) < 1:
        print("用法: python check_mount_order.py <backend/app 目录或应用文件> [--mode spa|api|auto]")
        print("例:   python check_mount_order.py <项目>/backend/app --mode spa")
        print()
        print("  spa  同源托管 SPA（后端同时提供前端产物）——挂载顺序是硬约束")
        print("  api  纯后端 API（前端独立部署）——无回退路由，无此风险")
        print("  auto 自动判定（默认）")
        return 2

    root = Path(positional[0])
    if not root.exists():
        print(f"[FAIL] 路径不存在: {root}")
        return 1

    # auto 模式：先探测是否存在 catch-all 回退路由
    effective_mode = mode
    if mode == "auto":
        effective_mode = "spa" if _has_catchall(root) else "api"

    violations = find_violations(root, effective_mode)

    if not violations:
        if effective_mode == "api":
            print("[PASS] 纯 API 模式：未发现 SPA 回退路由，静态挂载顺序不构成风险")
            print("       （若本项目改为同源托管 SPA，请加 --mode spa 重跑）")
        else:
            print("[PASS] 静态挂载顺序正确：所有 mount 都定义在 SPA 回退路由之前")
            print("       （手册 §2.1：否则图片请求会被回退成 index.html，表现为「页面能开、图片全 404」）")
        return 0

    print(f"[FAIL] 发现 {len(violations)} 处静态挂载位置不当：")
    for f, mount_line, ref_line, path in violations:
        print(f"  {f}:{mount_line} 挂载 {path!r} 晚于第 {ref_line} 行")
    print()
    print("  修法：把所有 app.mount(...) 移到业务路由与 SPA 回退路由之前。")
    print("  正确顺序：静态挂载 → 业务路由 → SPA 回退。")
    print("  症状：页面能开，但图片/静态资源全部 404（浏览器拿到 200 + HTML，不报错，极隐蔽）。")
    return 1


def _has_catchall(root: Path) -> bool:
    """探测目录/文件内是否存在 catch-all 回退路由。"""
    if root.is_file():
        targets = [root]
    else:
        targets = [p for p in root.rglob("*.py") if "__pycache__" not in str(p)]
    for f in targets:
        try:
            text = f.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line in text.splitlines():
            if CATCHALL_ROUTE_RE.search(line) and SINGLE_SEGMENT_PARAM_RE.search(line):
                return True
    return False


if __name__ == "__main__":
    sys.exit(main())
