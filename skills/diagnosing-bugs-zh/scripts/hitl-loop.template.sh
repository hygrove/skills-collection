#!/usr/bin/env bash
# 人在回路（Human-in-the-loop）复现循环。
# 复制本文件，编辑下面的步骤，然后运行它。
# Agent 运行脚本；用户在其终端里按提示操作。
#
# 用法（Usage）：
#   bash hitl-loop.template.sh
#
# 两个辅助函数（helpers）：
#   step "<指令>"          → 显示指令，等待按回车
#   capture VAR "<问题>"      → 显示问题，把回答读入变量 VAR
#
# 最后，捕获的值以 KEY=VALUE 形式打印，供 agent 解析。
#
# `capture` 把其值回显到终端，agent 从那里读取，
# 因此用它捕获观察结果，而把"登录"之类留给用户当作一个 `step`。

set -euo pipefail

step() {
  printf '\n>>> %s\n' "$1"
  read -r -p "    [完成后按回车] " _
}

capture() {
  local var="$1" question="$2" answer
  printf '\n>>> %s\n' "$question"
  read -r -p "    > " answer
  printf -v "$var" '%s' "$answer"
}

# --- 编辑以下部分 ---------------------------------------------------------

step "在 http://localhost:3000 打开应用并登录。"

capture ERRORED "点击 'Export' 按钮。它抛出了错误吗？（y/n）"

capture ERROR_MSG "粘贴错误消息（或 'none'）："

# --- 编辑以上部分 ---------------------------------------------------------

printf '\n--- 已捕获 ---\n'
printf 'ERRORED=%s\n' "$ERRORED"
printf 'ERROR_MSG=%s\n' "$ERROR_MSG"
