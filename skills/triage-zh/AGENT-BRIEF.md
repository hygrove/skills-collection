# 撰写 Agent 简报（Writing Agent Briefs）

一份 agent 简报，是在一个 GitHub issue 或 PR 转移到 `ready-for-agent` 时发布在其上的、结构化的评论。它是 AFK agent 将依凭的权威规格说明。原始的 issue 正文与讨论是背景：agent 简报才是契约。

简报陈述**agent 应该做什么**，这延伸到两个面：对 issue 来说，是从无到有构建改动；对 PR 来说，是对*现有 diff* 还剩下的事：把它做完、补上缺口、处理评审意见。无论哪种，原则相同；下面的 PR 示例展示了区别。

## 原则（Principles）

### 耐久优于精确（Durability over precision）

issue 可能在 `ready-for-agent` 里一待就是几天或几周。代码库会在此期间变化。写简报要让它在文件被重命名、移动或重构后依然有用。

- **要**描述接口、类型和行为的契约
- **要**点名 agent 应当寻找或修改的具体类型、函数签名或配置形态
- **不要**引用文件路径：它们会过时
- **不要**引用行号
- **不要**假设当前的实现结构会保持不变

### 行为化，而非过程化（Behavioral, not procedural）

描述系统**应该做什么**，而不是**如何实现它**。agent 会重新探索代码库，并做出自己的实现决策。

- **好：** "`SkillConfig` 类型应当接受一个可选的、类型为 `CronExpression` 的 `schedule` 字段"
- **坏：** "打开 src/types/skill.ts，在第 42 行加一个 schedule 字段"
- **好：** "当用户不带参数运行 `/triage-zh` 时，他们应当看到一个需要关注的 issue 摘要"
- **坏：** "在主处理函数里加一个 switch 语句"

### 完整的验收标准（Complete acceptance criteria）

agent 需要知道何时算完成。每份 agent 简报都必须有具体的、可测试的验收标准。每条标准都应可独立验证。

- **好：** "运行 `gh issue list --label needs-triage` 返回的是经过初步分类的 issue"
- **坏：** "分诊应当正常工作"

### 显式的范围边界（Explicit scope boundaries）

声明什么不在范围内。这能防止 agent 镀金（gold-plating）或对相邻功能做假设。

## 模板（Template）

```markdown
## Agent Brief

**Category:** bug / enhancement
**Summary:** 关于需要发生什么的一句话描述

**Current behavior:**
描述现在发生什么。对 bug，这就是坏掉的行为。
对 enhancement，这是该 feature 所依托的现状。

**Desired behavior:**
描述 agent 工作完成后应当发生什么。
对边界情形和错误条件要具体。

**Key interfaces:**
- `TypeName`：需要改什么、为什么
- `functionName()` 返回类型：当前返回什么 vs 应当返回什么
- 配置形态：任何需要的新配置项

**Acceptance criteria:**
- [ ] 具体、可测试的标准 1
- [ ] 具体、可测试的标准 2
- [ ] 具体、可测试的标准 3

**Out of scope:**
- 在这个 issue 里不应被改动或处理的事
- 可能看似相关、但实则独立的功能
```

## 示例（Examples）

### 好的 agent 简报（bug）

```markdown
## Agent Brief

**Category:** bug
**Summary:** 技能描述在单词中间被截断，产生坏掉的输出

**Current behavior:**
当技能描述超过 1024 个字符时，它被精确地在第 1024 个字符处截断，
不管单词边界。这产生以单词中途结尾的描述（例如 "Use when the user wants to confi"）。

**Desired behavior:**
截断应当在 1024 字符之前的最后一个单词边界处断开，
并追加 "..." 表示被截断。

**Key interfaces:**
- `SkillMetadata` 类型的 `description` 字段：无需改类型，
  但填充它的校验/处理逻辑需要尊重单词边界
- 任何读取 SKILL.md frontmatter 并抽取 description 的函数

**Acceptance criteria:**
- [ ] 小于 1024 字符的描述保持不变
- [ ] 大于 1024 字符的描述在 1024 字符之前的最后一个单词边界处被截断
- [ ] 被截断的描述以 "..." 结尾
- [ ] 含 "..." 的总长度不超过 1024 字符

**Out of scope:**
- 改动 1024 字符上限本身
- 多行描述支持
```

### 好的 agent 简报（enhancement）

```markdown
## Agent Brief

**Category:** enhancement
**Summary:** 添加 `.out-of-scope/` 目录支持，以追踪被拒绝的功能请求

**Current behavior:**
当一个功能请求被拒绝时，issue 被加上 `wontfix` 标签并附一条评论关闭。
没有任何持久化的记录留存决策或理由。
未来类似的请求需要维护者回忆或搜索先前的讨论。

**Desired behavior:**
被拒绝的功能请求应当被记录在 `.out-of-scope/<concept>.md` 文件里，
捕获决策、理由，以及指向所有请求过该功能的 issue 的链接。
在分诊新 issue 时，应检查这些文件是否有匹配。

**Key interfaces:**
- `.out-of-scope/` 里的 markdown 文件格式：每个文件应有一个
  `# Concept Name` 标题、一行 `**Decision:**`、一行 `**Reason:**`，
  以及一个带 issue 链接的 `**Prior requests:**` 列表
- 分诊工作流应当尽早读取所有 `.out-of-scope/*.md` 文件，
  并按概念相似度将新 issue 与它们匹配

**Acceptance criteria:**
- [ ] 以 wontfix 关闭一个功能时，创建/更新 `.out-of-scope/` 里的一个文件
- [ ] 该文件包含决策、理由，以及到被关闭 issue 的链接
- [ ] 如果已存在匹配的 `.out-of-scope/` 文件，新 issue 被追加到它的
      "Prior requests" 列表，而非创建重复
- [ ] 在分诊期间，现有 `.out-of-scope/` 文件被检查并在新 issue 匹配先前提拒时摆出来

**Out of scope:**
- 自动匹配（由人工确认匹配）
- 重开先前被拒的功能
- bug 报告（只有 enhancement 的拒绝才进 `.out-of-scope/`）
```

### 好的 agent 简报（PR）

对 PR，"Current behavior"描述 diff 的状态，简报要求 agent 把它做完或修好，而非从零构建。

```markdown
## Agent Brief

**Category:** enhancement
**Summary:** 完成贡献者的 `triage-zh list` 的 `--json` 输出标志

**Current behavior:**
该 PR 添加了一个把 issue 列表序列化为 JSON 的 `--json` 标志。happy path 可用，
且 diff 符合项目的命令结构。还剩两处缺口：错误仍作为人类文本（而非 JSON）打印，
且新标志没有测试覆盖。

**Desired behavior:**
在 `--json` 下，所有输出（含错误）都是 stdout 上格式良好的 JSON，
且命令的退出码不变。当标志缺席时，现有人类可读输出原封不动。

**Key interfaces:**
- 命令的错误路径应当在 `--json` 下发出 `{ "error": string }`，
  而非纯文本错误
- 复用 PR 已经添加的现有序列化器；不要引入第二个

**Acceptance criteria:**
- [ ] `triage-zh list --json` 对成功与错误两种情况都发出合法 JSON
- [ ] 退出码与无 JSON 的命令一致
- [ ] 一个测试覆盖 `--json` 的成功输出与一处错误情形
- [ ] 默认（无 JSON）输出逐字节不变

**Out of scope:**
- 给任何其它命令加 `--json`
- 改变 PR 已定义的成功 payload 的 JSON 形态
```

### 坏的 agent 简报（Bad agent brief）

```markdown
## Agent Brief

**Summary:** 修分诊的 bug

**What to do:**
分诊那玩意儿坏了。看看主文件然后修好它。
第 150 行附近的函数有问题。

**Files to change:**
- src/triage-zh/handler.ts (line 150)
- src/types.ts (line 42)
```

这很坏，因为：
- 没有 category
- 描述模糊（"分诊那玩意儿坏了"）
- 引用了会过时的文件路径和行号
- 没有验收标准
- 没有范围边界
- 没有对当前行为 vs 期望行为的描述
