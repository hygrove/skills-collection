---
name: setup-matt-pocock-skills-zh
description: "为本仓库配置工程类技能：搭建问题追踪器、分诊标签词汇，以及领域文档布局。在其他工程技能首次使用前运行一次。"
disable-model-invocation: true
---

# 配置 Matt Pocock 的技能（Setup Matt Pocock's Skills）

为工程类技能所假定的"每仓库配置"搭好脚手架：

- **Issue tracker 问题追踪器**：问题（issues）存放的位置（默认 GitHub；开箱即支持本地 markdown）
- **Triage labels 分诊标签**：五个规范性分诊角色所用的字符串
- **Domain docs 领域文档**：`CONTEXT.md` 与 ADR 存放的位置，以及阅读它们的消费方规则

这是一个由提示词驱动的技能，不是确定性的脚本。先探索、呈现你的发现、与用户确认，然后再写入。

## 流程

### 1. 探索

查看当前仓库，了解它的起始状态。读取一切已存在的东西；不要假设：

- `git remote -v` 与 `.git/config`：这是一个 GitHub 仓库吗？是哪个？
- 仓库根目录的 `AGENTS.md` 与 `CLAUDE.md`：两者是否存在？其中是否已有 `## Agent skills` 小节？
- 仓库根目录的 `CONTEXT.md` 与 `CONTEXT-MAP.md`
- `docs/adr/` 以及任何 `src/*/docs/adr/` 目录
- `docs/agents/`：本技能之前的产出是否已存在？
- `.scratch/`：说明本地 markdown 问题追踪器约定已在使用的迹象
- `triage` 技能是否已安装？（本技能同级的 `triage` 技能文件夹，或你的可用技能列表里有 `triage`。）这决定是否运行 B 节。
- Monorepo（单体多包仓库）信号：`pnpm-workspace.yaml`、`package.json` 中的 `workspaces` 字段，或被填充的 `packages/*` 且自带 `src/`。这些仅出现在真正大型的多包仓库中；若没有，说明是单上下文——几乎每个仓库都是如此。

### 2. 呈现发现并询问

总结哪些已存在、哪些缺失。然后按顺序处理各小节。一个小节、一个答案，再下一个。

每个小节的引导语给出推荐答案，让用户一句话就能接受。只有当选择确实会分叉时才给一行解释；若探索已经定论则整个跳过该小节（当 `triage` 未安装时跳过 B 节，当没有 monorepo 时跳过 C 节）。

**A 节：问题追踪器。**

> 解释：所谓"问题追踪器"就是本仓库问题的存放处。像 `to-tickets`、`triage`、`to-spec` 这样的技能会往里读、往里写。它们需要知道是调用 `gh issue create`、还是在 `.scratch/` 下写一个 markdown 文件，或是遵循你描述的其它流程。挑一个你真正用来跟踪本仓库工作的地方。

默认姿态：这些技能是为 GitHub 设计的。如果 `git remote` 指向 GitHub，就提议用 GitHub。如果指向 GitLab（`gitlab.com` 或自托管主机），就提议用 GitLab。否则（或用户偏好），提供：

- **GitHub**：问题存放在仓库的 GitHub Issues（使用 `gh` CLI）
- **GitLab**：问题存放在仓库的 GitLab Issues（使用 [`glab`](https://gitlab.com/gitlab-org/cli) CLI）
- **本地 markdown**：问题以文件形式存放在本仓库的 `.scratch/<feature>/` 下（适合个人项目或无远程的仓库）
- **其他**（Jira、Linear 等）：请用户用一段话描述流程；技能会把它作为自由格式散文记录

把选择记录到 `docs/agents/issue-tracker.md`。GitHub 和 GitLab 模板都带一个"将 PR 视为请求入口"的标志，默认**关闭**。保持关闭、不要提起它：想要把外部 PR 纳入分诊队列的用户日后可以在文件里翻转该标志。

**B 节：分诊标签词汇。** 如果 `triage` 未安装（探索已告诉你），整节跳过，因为未安装的技能不需要标签。

如果已安装，只问一个问题：

> 你想保留默认的分诊标签吗？（推荐：**是**）

默认值是五个规范性角色，每个标签字符串等于其名称：`needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human`、`wontfix`。选**是**就原样写入。只有当用户说"否"（通常是因为他们的追踪器已经用了别的名字，比如用 `bug:triage` 表示 `needs-triage`）时，才收集覆盖项，以便 `triage` 套用已有标签而非创建重复项。

**C 节：领域文档。** 默认**单上下文**（仓库根目录一个 `CONTEXT.md` + `docs/adr/`）。这适配几乎所有仓库；直接写入，不问。

仅在探索发现 monorepo 信号时，才提供**多上下文**（根目录 `CONTEXT-MAP.md` 指向各上下文的 `CONTEXT.md` 文件）选项。然后确认他们想要哪种布局。

### 3. 确认与编辑

向用户展示草稿：

- 要加入正在编辑的 `CLAUDE.md` / `AGENTS.md` 的 `## Agent skills` 块（选择规则见第 4 步）
- `docs/agents/issue-tracker.md`、`docs/agents/domain.md`、`docs/agents/triage-labels.md`（最后一项仅当 `triage` 已安装时）的内容

让他们在写入前先编辑。

### 4. 写入

**挑选要编辑的文件：**

- 如果 `CLAUDE.md` 存在，编辑它。
- 否则如果 `AGENTS.md` 存在，编辑它。
- 如果两者都不存在，问用户要创建哪一个；不要替他们选。

当 `CLAUDE.md` 已存在时绝不要创建 `AGENTS.md`（反之亦然）；始终编辑那个已经存在的。

如果在所选文件中已存在 `## Agent skills` 块，就地更新其内容，而不是追加一个重复块。不要覆盖用户对周围小节的编辑。

该块：

```markdown
## Agent skills

### Issue tracker

[一行说明问题在哪里被追踪]。参见 `docs/agents/issue-tracker.md`。

### Triage labels

[一行说明标签词汇]。参见 `docs/agents/triage-labels.md`。

### Domain docs

[一行说明布局："single-context" 或 "multi-context"]。参见 `docs/agents/domain.md`。
```

仅在 `triage` 已安装且 B 节运行时，才包含 `### Triage labels` 子块并写入 `docs/agents/triage-labels.md`。否则两者都省略。

然后用本技能文件夹中的种子模板作为起点写入文档文件：

- [issue-tracker-github.md](./issue-tracker-github.md)：GitHub 问题追踪器
- [issue-tracker-gitlab.md](./issue-tracker-gitlab.md)：GitLab 问题追踪器
- [issue-tracker-local.md](./issue-tracker-local.md)：本地 markdown 问题追踪器
- [triage-labels.md](./triage-labels.md)：标签映射（仅当 `triage` 已安装）
- [domain.md](./domain.md)：领域文档消费方规则 + 布局

对于"其他"类问题追踪器，用用户的描述从头写 `docs/agents/issue-tracker.md`。

### 5. 完成

告诉用户配置已完成，哪些工程类技能现在会从这些文件读取。提及他们日后可以直接编辑 `docs/agents/*.md`；只有想切换问题追踪器或从头重来时才需要重新运行本技能。
