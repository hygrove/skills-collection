# 问题追踪器：GitLab（Issue tracker: GitLab）

本仓库的 issues 与 specs 以 GitLab issues 形式存在。所有操作都用 [`glab`](https://gitlab.com/gitlab-org/cli) CLI。

## 约定（Conventions）

- **创建 issue**：`glab issue create --title "..." --description "..."`。多行描述用 heredoc。传 `--description -` 打开编辑器。
- **读取 issue**：`glab issue view <number> --comments`。用 `-F json` 拿机器可读输出。
- **列出 issues**：`glab issue list -F json` 配合合适的 `--label` 过滤。
- **评论 issue**：`glab issue note <number> --message "..."`。GitLab 把评论叫做 "notes"。
- **添加 / 移除标签**：`glab issue update <number> --label "..."` / `--unlabel "..."`。多个标签可用逗号分隔，或重复该 flag。
- **关闭**：`glab issue close <number>`。`glab issue close` 不接受关闭评论，所以先用 `glab issue note <number> --message "..."` 把解释发上去，再关闭。
- **合并请求（Merge requests）**：GitLab 把 PR 叫做"合并请求（merge requests）"。用 `glab mr create`、`glab mr view`、`glab mr note` 等，形态与 `gh pr ...` 一致，只是把 `pr` 换成 `mr`、`comment`/`--body` 换成 `note`/`--message`。

从 `git remote -v` 推断仓库；在 clone 内部运行时 `glab` 自动推断。

## 把合并请求当作分诊面（Merge requests as a triage-zh surface）

**MRs as a request surface（MR 作为请求入口）：no（否）。** _（若本仓库把外部合并请求当作功能请求，改为 `yes`；`/triage-zh` 会读取这个标志。）_

当设为 `yes` 时，MR 跑与 issue 同样的标签和状态，使用 `glab mr` 的等价命令：

- **读取 MR**：`glab mr view <number> --comments` 以及 `glab mr diff <number>` 看 diff。
- **列出待分诊的外部 MR**：`glab mr list -F json`，然后只保留作者不是项目成员/拥有者的 MR（一个贡献者的 MR，而非维护者进行中的工作）。
- **评论 / 打标签 / 关闭**：`glab mr note`、`glab mr update --label`/`--unlabel`、`glab mr close`。

与 GitHub 不同，GitLab 的 issue 与 MR 编号是分开的，所以一旦你知道维护者意指哪个面，`#42` 就无歧义。

## 当技能说"发布到问题追踪器"（publish to the issue tracker）

创建一个 GitLab issue。

## 当技能说"抓取相关工单"（fetch the relevant ticket）

运行 `glab issue view <number> --comments`。

## 寻路操作（Wayfinding operations）

由 `/wayfinder-zh` 使用。**地图（map）** 是一个带**子** issue 作为工单的单一 issue。

- **地图（Map）**：一个带 `wayfinder-zh:map` 标签的单一 issue，装着 Notes / Decisions-so-far / Fog 正文。`glab issue create --label wayfinder-zh:map`。（在提供原生 epics 的 GitLab 套餐层级上，一个 epic 也可以承载地图；一个带标签的 issue 在哪都行。）
- **子工单（Child ticket）**：一个在描述顶部带着 `Part of #<map>`、并带 `wayfinder-zh:<type>`（`research-zh`/`prototype-zh`/`grilling-zh`/`task`）标签的 issue。一旦被认领，工单被指派给正在驱动这张地图的开发者。
- **阻塞（Blocking）**：GitLab 的**原生阻塞链接**，即规范、在 UI 上可见的表示。用 `/blocked_by #<n>` 快捷动作添加，作为一个 note 发布（`glab issue note <child> --message "/blocked_by #<blocker>"`）。原生阻塞链接是 Premium/Ultimate 功能；在免费层级（或不可用时）退回到描述顶部的 `Blocked by: #<n>, #<n>` 一行。一张工单在其每个阻塞者都关闭时即解除阻塞。
- **前沿查询（Frontier query）**：`glab issue list -F json` 限定在地图的子项内，丢弃任何有未关闭阻塞者：一个指向未关闭 issue 的原生 `blocked_by` 链接（`glab api projects/:id/issues/:iid/links`），或 `Blocked by` 行里有一个未关闭 issue，或有一个指派者；地图顺序中第一个胜出。
- **认领（Claim）**：`glab issue update <n> --assignee @me`，这是会话的第一次写入。
- **解决（Resolve）**：`glab issue note <n> --message "<answer>"`，然后 `glab issue close <n>`，然后向地图的 Decisions-so-far 追加一个上下文指针（梗概 + 链接）。
