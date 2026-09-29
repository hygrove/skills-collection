# 问题追踪器：GitHub（Issue tracker: GitHub）

本仓库的 issues 与 specs 以 GitHub issues 形式存在。所有操作都用 `gh` CLI。

## 约定（Conventions）

- **创建 issue**：`gh issue create --title "..." --body "..."`。多行正文用 heredoc。
- **读取 issue**：`gh issue view <number> --comments`，用 `jq` 过滤评论，并同时抓取标签。
- **列出 issues**：`gh issue list --state open --json number,title,body,labels,comments --jq '[.[] | {number, title, body, labels: [.labels[].name], comments: [.comments[].body]}]'`，配合合适的 `--label` 与 `--state` 过滤。
- **评论 issue**：`gh issue comment <number> --body "..."`
- **添加 / 移除标签**：`gh issue edit <number> --add-label "..."` / `--remove-label "..."`
- **关闭**：`gh issue close <number> --comment "..."`

从 `git remote -v` 推断仓库；在 clone 内部运行时 `gh` 自动推断。

## 把 PR 当作分诊面（Pull requests as a triage-zh surface）

**PRs as a request surface（PR 作为请求入口）：no（否）。** _（若本仓库把外部 PR 当作功能请求，改为 `yes`；`/triage-zh` 会读取这个标志。）_

当设为 `yes` 时，PR 跑与 issue 同样的标签和状态，使用 `gh pr` 的等价命令：

- **读取 PR**：`gh pr view <number> --comments` 以及 `gh pr diff <number>` 看 diff。
- **列出待分诊的外部 PR**：`gh pr list --state open --json number,title,body,labels,author,authorAssociation,comments` 然后只保留 `authorAssociation` 为 `CONTRIBUTOR`、`FIRST_TIME_CONTRIBUTOR` 或 `NONE` 的（丢弃 `OWNER`/`MEMBER`/`COLLABORATOR`）。
- **评论 / 打标签 / 关闭**：`gh pr comment`、`gh pr edit --add-label`/`--remove-label`、`gh pr close`。

GitHub 在 issues 和 PR 之间共享同一个编号空间，所以一个孤零零的 `#42` 两者皆有可能：用 `gh pr view 42` 解析，失败则退回到 `gh issue view 42`。

## 当技能说"发布到问题追踪器"（publish to the issue tracker）

创建一个 GitHub issue。

## 当技能说"抓取相关工单"（fetch the relevant ticket）

运行 `gh issue view <number> --comments`。

## 寻路操作（Wayfinding operations）

由 `/wayfinder-zh` 使用。**地图（map）** 是一个带**子** issue 作为工单的单一 issue。

- **地图（Map）**：一个带 `wayfinder-zh:map` 标签的单一 issue，装着 Notes / Decisions-so-far / Fog 正文。`gh issue create --label wayfinder-zh:map`。
- **子工单（Child ticket）**：一个作为 GitHub 子 issue 链接到地图的 issue（`gh api` 操作 sub-issues 端点）。当子 issue 未启用时，把子项加进地图正文的任务清单，并在子正文顶部写上 `Part of #<map>`。标签：`wayfinder-zh:<type>`（`research-zh`/`prototype-zh`/`grilling-zh`/`task`）。一旦被认领，工单被指派给正在驱动这张地图的开发者。
- **阻塞（Blocking）**：GitHub 的**原生 issue 依赖**，即规范、在 UI 上可见的表示。用 `gh api --method POST repos/<owner>/<repo>/issues/<child>/dependencies/blocked_by -F issue_id=<blocker-db-id>` 加一条边，其中 `<blocker-db-id>` 是阻塞者的数字**数据库 id**（`gh api repos/<owner>/<repo>/issues/<n> --jq .id`，*不是* `#number` 或 `node_id`）。GitHub 报告 `issue_dependencies_summary.blocked_by`（仅未关闭的阻塞者，即实时闸门）。当依赖不可用，退回到子正文顶部的 `Blocked by: #<n>, #<n>` 一行。一张工单在其每个阻塞者都关闭时即解除阻塞。
- **前沿查询（Frontier query）**：列出地图的开放子项（`gh issue list --state open`，限定在地图的子 issue / 任务清单内），丢弃任何有未关闭阻塞者（`issue_dependencies_summary.blocked_by > 0`，或 `Blocked by` 行里有一个开放 issue）或指派者的；地图顺序中第一个胜出。
- **认领（Claim）**：`gh issue edit <n> --add-assignee @me`，这是会话的第一次写入。
- **解决（Resolve）**：`gh issue comment <n> --body "<answer>"`，然后 `gh issue close <n>`，然后向地图的 Decisions-so-far 追加一个上下文指针（梗概 + 链接）。
