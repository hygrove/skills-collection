#!/usr/bin/env bash
#
# 向导（wizard-zh）一步步引导人类完成一项手动流程。
# 由 /wizard-zh 技能生成。
#
# "STAGES" 标记之上的所有内容都是向导库：不要手动编辑它。
# 在标记之下编写每个步骤对应的 stage。

set -euo pipefail

# ──────────────────────────────────────────────────────────────────────────
# 向导库：愉悦、一致的 UX，在每个向导里都一模一样。
# ──────────────────────────────────────────────────────────────────────────

if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && [[ "$(tput colors 2>/dev/null || echo 0)" -ge 8 ]]; then
  BOLD=$(tput bold); DIM=$(tput dim); RESET=$(tput sgr0)
  BLUE=$(tput setaf 4); GREEN=$(tput setaf 2); YELLOW=$(tput setaf 3); RED=$(tput setaf 1)
else
  BOLD=""; DIM=""; RESET=""; BLUE=""; GREEN=""; YELLOW=""; RED=""
fi

# 作者在 stages 段顶部设置这个值。
TOTAL_STAGES=0

_STAGE_INDEX=0
ENV_FILE="${ENV_FILE:-.env}"
WRITTEN_ENV=()    # 本次运行写入 ENV_FILE 的 KEY
WRITTEN_SECRET=() # 本次运行设置的 secret NAME
SKIPPED=()        # 我们做不了的事（例如缺少 gh）

# _clear 清屏，使屏幕上只剩当前步骤。当输出不是终端时为空操作，
# 这样管道化的日志仍可读。
_clear() {
  [[ -t 1 ]] || return 0
  if command -v tput >/dev/null 2>&1; then tput clear; else printf '\033[2J\033[3J\033[H'; fi
}

# banner "标题" 显示开场帧：这个向导是做什么的。
banner() {
  _clear
  printf '\n%s%s  %s%s\n' "$BOLD" "$BLUE" "$1" "$RESET"
  printf '%s  %s 个阶段%s\n\n' "$DIM" "$TOTAL_STAGES" "$RESET"
  printf '%s  你负责操作浏览器；这个向导会精确告诉你做什么，并\n' "$DIM"
  printf '  捕获你拷回的值。随时可用 Ctrl-C 停下，之后再重跑，\n'
  printf '  因为它记得已经保存过的值。%s\n' "$RESET"
  pause "准备好了吗？"
}

# stage "名称" 清屏，然后宣布一个阶段并显示进度。
# 清屏使屏幕上只剩当前步骤。
stage() {
  _clear
  _STAGE_INDEX=$((_STAGE_INDEX + 1))
  printf '\n%s%s▸ 阶段 %s/%s · %s%s\n' \
    "$BOLD" "$BLUE" "$_STAGE_INDEX" "$TOTAL_STAGES" "$1" "$RESET"
}

# say "..." 打印一行普通指令。
say()  { printf '  %s\n' "$1"; }
# step "..." 是人类在浏览器里执行的一个、带有编号感的动作。
step() { printf '  %s•%s %s\n' "$BLUE" "$RESET" "$1"; }
note() { printf '  %s%s%s\n' "$DIM" "$1" "$RESET"; }
warn() { printf '  %s⚠ %s%s\n' "$YELLOW" "$1" "$RESET"; }

# open_url URL 在人类的浏览器里打开它，跨平台（含 WSL）。
open_url() {
  local url="$1"
  printf '  %s↗ 正在打开%s %s\n' "$GREEN" "$RESET" "$url"
  { if   command -v wslview     >/dev/null 2>&1; then wslview "$url"
    elif command -v explorer.exe >/dev/null 2>&1; then explorer.exe "$url"
    elif command -v xdg-open    >/dev/null 2>&1; then xdg-open "$url"
    elif command -v open        >/dev/null 2>&1; then open "$url"
    else warn "无法打开浏览器；请手动访问：$url"; fi
  } >/dev/null 2>&1 || warn "无法打开浏览器，请手动访问：$url"
}

# pause "信息" 等待人类确认他们已完成手动部分。
pause() {
  printf '  %s%s%s ' "$DIM" "${1:-按回车继续}" "$RESET"
  read -r _ || true
}

# confirm "问题" 是一个 y/N 闸门；回答 yes 时返回成功。
confirm() {
  local reply=""
  printf '  %s？ %s [y/N] ' "$YELLOW" "$1"
  read -r reply || true
  [[ "$reply" =~ ^[Yy] ]]
}

# _existing KEY：ENV_FILE 中 KEY 的当前值（若有）。
_existing() {
  [[ -f "$ENV_FILE" ]] || return 1
  local line; line=$(grep -E "^${1}=" "$ENV_FILE" | tail -n1) || return 1
  printf '%s' "${line#*=}"
}

# ask KEY "提示" 把一个值读入 $KEY。重跑时把现有 .env 值作为默认（回车保留）。
# 可见输入（非机密）。
ask() {
  local key="$1" prompt="$2" current input
  current=$(_existing "$key" || true)
  if [[ -n "$current" ]]; then
    printf '  %s%s%s %s[回车保留当前值]%s ' "$BOLD" "$prompt" "$RESET" "$DIM" "$RESET"
  else
    printf '  %s%s%s ' "$BOLD" "$prompt" "$RESET"
  fi
  read -r input || true
  [[ -z "$input" && -n "$current" ]] && input="$current"
  printf -v "$key" '%s' "$input"
}

# ask_secret KEY "提示" 类似 ask，但输入被隐藏。
ask_secret() {
  local key="$1" prompt="$2" current input
  current=$(_existing "$key" || true)
  if [[ -n "$current" ]]; then
    printf '  %s%s%s %s[回车保留当前值]%s ' "$BOLD" "$prompt" "$RESET" "$DIM" "$RESET"
  else
    printf '  %s%s%s ' "$BOLD" "$prompt" "$RESET"
  fi
  read -rs input || true
  printf '\n'
  [[ -z "$input" && -n "$current" ]] && input="$current"
  printf -v "$key" '%s' "$input"
}

# write_env KEY VALUE 把 KEY=VALUE upsert 进 ENV_FILE（创建它；替换任何现有行）。
# 幂等。
write_env() {
  local key="$1" value="$2" tmp
  touch "$ENV_FILE"
  tmp=$(mktemp)
  grep -vE "^${key}=" "$ENV_FILE" > "$tmp" || true
  printf '%s=%s\n' "$key" "$value" >> "$tmp"
  mv "$tmp" "$ENV_FILE"
  WRITTEN_ENV+=("$key")
  printf '  %s✓ 已写入%s %s → %s\n' "$GREEN" "$RESET" "$key" "$ENV_FILE"
}

# set_secret NAME VALUE 通过 gh 设置一个 GitHub Actions 仓库 secret。
# 若 gh 不可用或未认证，则退回为一个警告（并记录下来）。
set_secret() {
  local name="$1" value="$2"
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if printf '%s' "$value" | gh secret set "$name" >/dev/null 2>&1; then
      WRITTEN_SECRET+=("$name")
      printf '  %s✓ 已设置%s GitHub secret %s\n' "$GREEN" "$RESET" "$name"
      return
    fi
  fi
  SKIPPED+=（"GitHub secret $name（手动设置：gh secret set $name）"）
  warn "已跳过 GitHub secret $name：gh 未就绪；稍后设置"
}

# set_var NAME VALUE 设置一个 GitHub Actions 仓库变量（非机密）。
set_var() {
  local name="$1" value="$2"
  if command -v gh >/dev/null 2>&1 && gh auth status >/dev/null 2>&1; then
    if gh variable set "$name" --body "$value" >/dev/null 2>&1; then
      printf '  %s✓ 已设置%s GitHub 变量 %s\n' "$GREEN" "$RESET" "$name"
      return
    fi
  fi
  SKIPPED+=（"GitHub 变量 $name"）
  warn "已跳过 GitHub 变量 $name，gh 未就绪；稍后设置"
}

# finish 清屏，然后显示一份收尾摘要，列出所有已配置项。
finish() {
  _clear
  printf '\n%s%s  ✓ 设置完成%s\n' "$BOLD" "$GREEN" "$RESET"
  (( ${#WRITTEN_ENV[@]} ))    && note "向 $ENV_FILE 写入了 ${#WRITTEN_ENV[@]} 个值：${WRITTEN_ENV[*]}"
  (( ${#WRITTEN_SECRET[@]} )) && note "设置了 ${#WRITTEN_SECRET[@]} 个 GitHub secret：${WRITTEN_SECRET[*]}"
  if (( ${#SKIPPED[@]} )); then
    printf '\n'; warn "仍需手动完成："
    for s in "${SKIPPED[@]}"; do note "  - $s"; done
  fi
  printf '\n'
}

# ──────────────────────────────────────────────────────────────────────────
# STAGES：编写此段。人类每走一步对应一个 stage()。
# 替换下面的示例。把你写的 stage 数量设到 TOTAL_STAGES。
# ──────────────────────────────────────────────────────────────────────────

TOTAL_STAGES=1

banner "Stripe 设置"

# ── 示例阶段：用你真实的步骤替换 ───────────────────────────────────────────
stage "Stripe：API 密钥"
say "我们将获取你的 Stripe 测试密钥，并存储供本地开发 + CI 使用。"
open_url "https://dashboard.stripe.com/test/apikeys"
step "在 API 密钥页面，复制 Publishable key（以 pk_test_ 开头）。"
ask STRIPE_PUBLISHABLE_KEY "粘贴 publishable key："
step "在 Secret key 那一行点击 'Reveal test key'，然后复制它。"
ask_secret STRIPE_SECRET_KEY "粘贴 secret key："
write_env STRIPE_PUBLISHABLE_KEY "$STRIPE_PUBLISHABLE_KEY"
write_env STRIPE_SECRET_KEY "$STRIPE_SECRET_KEY"
set_secret STRIPE_SECRET_KEY "$STRIPE_SECRET_KEY"   # CI 需要这个
# ──────────────────────────────────────────────────────────────────────────

finish
