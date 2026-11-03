#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""校验「可移植性」：路径与端口不得硬编码（异地克隆 / 云端部署的前提）。

为什么需要这个闸门：
    这类项目的部署目标常常是「先在本地跑通，再搬到云端」或「换个机器继续跑」。
    硬编码是这两件事最常见的阻塞点，而且**症状是运行时才暴露**，不是构建期：

      · 硬编码绝对路径（`E:\\data\\`、`/Users/me/xxx`、`C:/Users/...`）
        → 换机器/换用户就找不到文件。Windows 换 Linux 更彻底：
          盘符分隔符与路径大小写都会炸。

      · 硬编码端口（`--port 8000`、`localhost:8000`）
        → 云端部署时平台注入 `PORT` 环境变量（Cloud Run / Heroku / K8s /
          容器平台的标准做法），写死端口会导致容器监听在错端口上，
          健康检查失败或流量进不来。**这是「本地能跑、云端起不来」的经典原因。**

    本脚本检查两类硬编码：
      ① 绝对路径字面量（盘符路径、UNC 路径、家目录绝对路径、POSIX 绝对路径）；
      ② 端口字面量（`:8000` / `port 8000` / `--port 8000` 这类固定端口）。

    ⚠️ 端口的合法例外：
      · 前端 vite 的 dev server 端口（5173）——只在开发期用，不影响生产；
      · 测试与校验脚本里的端口；
      · 注释与文档里的示例（会被剥离）。

用法：
    python check_portability.py <项目根目录或后端目录> [--allow-port 8000]...
    例：python check_portability.py <项目>/backend
    例：python check_portability.py ./backend --allow-port 8000 --allow-port 5173

退出码：0 = 通过；1 = 发现硬编码。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

# ── 绝对路径字面量 ───────────────────────────────────────────
# Windows 盘符路径：C:\... 或 C:/...
WIN_PATH_RE = re.compile(r"""["'`]([A-Za-z]:[\\/][^"'`\n]{2,120})["'`]""")
# UNC 路径：\\server\share
UNC_PATH_RE = re.compile(r"""["'`](\\\\[^"'`\n]{2,120})["'`]""")
# POSIX 家目录/绝对路径：/Users/... /home/... /root/... /var/... /opt/...
# ⚠️ 只匹配「明显的机器专属路径」，不匹配 /api /images 这类 URL 路径。
POSIX_HOME_RE = re.compile(
    r"""["'`](/(?:Users|home|root|var|opt|srv|mnt|Volumes|private|tmp)/[^"'`\n]{2,120})["'`]"""
)

# ── 端口字面量 ───────────────────────────────────────────────
#
# ⚠️ 判定必须精确，否则误报会淹掉真问题。
#   踩过的坑：用 `:\s*(\d{2,5})` 会把「阈值 5000」「比率 : 0.5」全当成端口。
#
# 只认这三种明确形态：
#   ① --port 8000 / --port=8000      （命令行参数）
#   ② port=8000 / PORT = 8000        （配置项，键名明确是 port）
#   ③ host:8000                       （冒号前必须是 host/IP/变量名，不是空格）
PORT_RE = re.compile(
    r"""(?:
          --port[=\s]+(\d{2,5})                        # --port 8000
        | \bport\s*[=:]\s*["']?(\d{2,5})               # port=8000 / PORT: 8000
        | \b(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\$\{?\w+\}?)\s*:\s*(\d{2,5})   # host:8000
    )""",
    re.IGNORECASE | re.VERBOSE,
)

# 注释与文档字符串（会被剥离，避免示例误报）
def strip_comments(text: str) -> str:
    """去掉 # 注释与 docstring，减少误报。"""
    # docstring
    text = re.sub(r'"""[\s\S]*?"""', "", text)
    text = re.sub(r"'''[\s\S]*?'''", "", text)
    # 行注释（简单处理：不处理字符串内的 #，宁可漏报也不误报）
    out = []
    for line in text.split("\n"):
        # 只剥离「# 之前没有引号」的行注释
        in_str = False
        quote = ""
        for i, ch in enumerate(line):
            if in_str:
                if ch == quote:
                    in_str = False
            elif ch in "\"'":
                in_str = True
                quote = ch
            elif ch == "#":
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def scan(root: Path, allow_ports: set[int]) -> list[tuple[str, int, str, str]]:
    """返回 (文件, 行号, 类型, 内容) 列表。"""
    hits: list[tuple[str, int, str, str]] = []

    if root.is_file():
        targets = [root]
    else:
        # 排除临时目录与虚拟环境：它们不是项目代码，扫了只会产生噪音。
        EXCLUDE_DIRS = {
            "node_modules", "__pycache__", ".venv", "venv", "env",
            ".scratch", ".git", "dist", "build", ".next", ".nuxt",
            ".pytest_cache", ".mypy_cache", "coverage",
        }
        targets = [
            p for p in root.rglob("*")
            if p.is_file()
            and p.suffix in (".py", ".ts", ".js", ".vue", ".sh", ".bat", ".ps1", ".yml", ".yaml", ".toml", ".cfg", ".ini")
            and not any(part in EXCLUDE_DIRS for part in p.parts)
        ]

    for f in targets:
        try:
            raw = f.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        lines = strip_comments(raw).split("\n")

        for idx, line in enumerate(lines, start=1):
            for rx, kind in (
                (WIN_PATH_RE, "Windows 绝对路径"),
                (UNC_PATH_RE, "UNC 绝对路径"),
                (POSIX_HOME_RE, "机器专属绝对路径"),
            ):
                for m in rx.finditer(line):
                    hits.append((str(f), idx, kind, m.group(1)))

            for m in PORT_RE.finditer(line):
                port_s = next((g for g in m.groups() if g), None)
                if not port_s:
                    continue
                try:
                    port = int(port_s)
                except ValueError:
                    continue
                if port in allow_ports:
                    continue
                # 排除明显不是端口的数值（如年份、比率分子）
                if port < 1024 or port > 65535:
                    continue
                hits.append((str(f), idx, "硬编码端口", m.group(0).strip()))

    return hits


def main() -> int:
    args = sys.argv[1:]
    positional: list[str] = []
    allow_ports: set[int] = set()
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--allow-port":
            if i + 1 >= len(args):
                print("[FAIL] --allow-port 需要一个端口号")
                return 2
            allow_ports.add(int(args[i + 1]))
            i += 2
            continue
        if a.startswith("--allow-port="):
            allow_ports.add(int(a.split("=", 1)[1]))
            i += 1
            continue
        if a.startswith("--"):
            i += 1
            continue
        positional.append(a)
        i += 1

    if len(positional) < 1:
        print("用法: python check_portability.py <项目目录> [--allow-port 端口]...")
        print("例:   python check_portability.py ./backend --allow-port 8000")
        print()
        print("  检查：绝对路径字面量（换机器就找不到）")
        print("        硬编码端口（云端注入 $PORT 时监听错端口）")
        print("  例外：--allow-port 声明「这个端口允许写死」")
        return 2

    root = Path(positional[0])
    if not root.exists():
        print(f"[FAIL] 路径不存在: {root}")
        return 1

    hits = scan(root, allow_ports)

    if not hits:
        print("[PASS] 未发现硬编码的绝对路径或端口（异地克隆 / 云端部署的前提）")
        print("       （路径应从 __file__ 或环境变量推导；端口应读 PORT 环境变量）")
        return 0

    print(f"[FAIL] 发现 {len(hits)} 处硬编码：")
    for f, line_no, kind, content in hits:
        print(f"  {f}:{line_no}  [{kind}] {content!r}")
    print()
    print("  修法：")
    print("    · 路径 → 从模块位置推导（Path(__file__).resolve().parent）")
    print("            或走环境变量（如 DATA_DIR = Path(os.getenv('APP_DATA_DIR', 默认值))）")
    print("    · 端口 → 读环境变量并给默认值：")
    print("              PORT = int(os.getenv('PORT', '8000'))   # 云端注入 PORT，端口即正确")
    print()
    print("  症状：本地能跑、云端起不来（健康检查失败 / 流量进不来），且构建期不报错。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
