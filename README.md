# skills-collection —— WorkBuddy 技能收集仓库

> 这是一个**给 AI 助手 WorkBuddy 装"技能/插件"的仓库**。
> 把平时跨机器、跨项目能复用的技能集中在这里，换电脑或重装时，拉下来复制一下就能用。

---

## 一、先搞懂：什么是"技能（skill）"？

用大白话讲：**技能就是一份写给 AI 看的"操作说明书"**。

- 你平时跟 WorkBuddy 说话，它是凭"常识"在答。
- 当你装了一个技能，就相当于塞给它一本**专项手册**（比如"怎么严酷地拷问一个方案""怎么把对话整理成开发工单"）。
- 装好之后，AI 要么**你点名让它用**，要么**它自己看场景自动用**。

类比：技能 ≈ 你给实习生发的《岗位 SOP 手册》。手册越多，它能干的专业活就越多。

**仓库里每一个技能，都是一个文件夹**，里面至少有一个 `SKILL.md`（说明书本体），有的还带参考资料。

---

## 二、这个仓库里有什么？（分两块，互不混淆）

为了"区分开来"，仓库里的技能清楚地分成两伙：

### 1）你自己的技能（作者原创，单独保留）

| 技能名 | 干嘛用的 |
|--------|----------|
| `extended-thinking` | 扩展性思维回答风格：先给核心答案，再延伸关联知识点、给避坑指南和真实坑提醒。 |

> 这是**你自己写的**，和下面那套"别人家的"严格分开，互不影响。

### 2）Matt Pocock 技能集（25 个，中英双语，来自社区）

这一套来自 Matt Pocock 开源的 `skills` 合集，覆盖**写代码、审代码、做架构、管 issue、教学**等场景。
我们做了**双语**：每个技能都有**英文原版**和**中文翻译版**两份。

- 英文版：用原名，例如 `grill-me`、`to-spec`
- 中文版：名字后面加 `-zh`，例如 `grill-me-zh`、`to-spec-zh`（加后缀是为了不让中英文"撞名"）

另外还配了 **2 个"路由技能"**（相当于导航地图，见第四节），帮你在 25 个里快速挑对的那个。

---

## 三、怎么装到自己的电脑？（小白 step by step）

### 第 1 步：找到 WorkBuddy 的技能目录

技能要放进下面这个目录（没有就自己建一个）：

| 系统 | 目录路径 |
|------|----------|
| Windows | `C:\Users\你的用户名\.workbuddy\skills\` |
| macOS / Linux | `~/.workbuddy/skills/` |

> 小提示：路径里的 `.workbuddy` 是个**隐藏文件夹**，文件管理器里默认看不见，直接地址栏粘贴路径就能进。

### 第 2 步：把技能文件夹复制进去

**方式 A：全部装（最简单，推荐先这样）**

把本仓库 `skills/` 目录下的**所有子文件夹**整体复制到你上面的 `skills/` 目录里：

```bash
# Windows（在仓库目录下执行，PowerShell 或 Git Bash 都行）
cp -r skills/* "$HOME/.workbuddy/skills/"

# macOS / Linux
cp -r skills/* ~/.workbuddy/skills/
```

**方式 B：只装一部分（更轻量）**

如果你只想用中文版 + 导航，可以只复制这几个：

```bash
# 只装中文技能 + 中文路由（示例，可自己挑）
cp -r skills/*-zh "$HOME/.workbuddy/skills/"
cp -r skills/mattpocock-menu-zh "$HOME/.workbuddy/skills/"
# 别忘了你自己的技能
cp -r skills/extended-thinking "$HOME/.workbuddy/skills/"
```

> 注意：中文技能名字带 `-zh`，**别把英文同名版也塞进去重复装**，选一种语言即可，除非你中英文都想留着对照。

### 第 3 步：让 WorkBuddy 认出来

- **WorkBuddy**：复制完**一般不用重启**，下一轮对话就自动发现新技能了。
- 如果没生效，关掉重开 WorkBuddy 一次即可。

---

## 四、装完后怎么用？（重点：别背，用导航）

技能分两类，用法不同：

### 类型 1：【自动型】—— 你啥都不用做

这类技能**场景对上了 AI 自己会加载**，你不用点名。比如你让它"审一下这段代码"，`code-review` 就自己蹦出来。
（具体哪些见下方清单里的"自动"标记。）

### 类型 2：【召唤型】—— 你得点名它才跑

这类技能必须你**主动叫名字**才会用。怎么叫？在 WorkBuddy 里输入斜杠 + 技能名：

```
/grill-me-zh
```

或者自然语言也行："用一下 grill-me-zh 技能"。

> 25 个里光"召唤型"就有 14 个，全背下来不现实。**解决办法：装那个"路由技能"当导航。**

### 强烈推荐：装一个"路由技能"当导航

仓库里有两个叫 `mattpocock-menu`（英文）/ `mattpocock-menu-zh`（中文）的技能，它就是**技能地图**：

- 你**只记它一个名字**即可。
- 遇到场景不知道用哪个，直接问它："我要做 X，该用哪个技能？"
- 它会从 25 个里挑出**唯一最合适**的那个，并告诉你该怎么叫它。

**新手最小配置（记 3 个就够用）：**
1. `mattpocock-menu-zh` —— 导航，问它"用哪个"
2. `grill-me-zh` —— 拷问/打磨你的想法方案
3. `to-spec-zh` + `to-tickets-zh` —— 把讨论成果变成开发规格与工单

其余的，等真实场景撞上了，问导航技能就知道用哪个了。

---

## 五、完整技能清单

### 你自己的技能

| 技能名 | 说明 |
|--------|------|
| `extended-thinking` | 扩展性思维回答：核心答案 → 关联扩展 → 避坑指南 → 真实坑。 |

### Matt Pocock 技能集 · 自动触发（11 个，场景对上 AI 自己跑）

| 英文 | 中文(-zh) | 一句话用途 |
|------|-----------|------------|
| `code-review` | `code-review-zh` | 对代码改动做评审 |
| `codebase-design` | `codebase-design-zh` | 用"深/浅模块"思路做架构设计 |
| `diagnosing-bugs` | `diagnosing-bugs-zh` | 系统化诊断 bug |
| `domain-modeling` | `domain-modeling-zh` | 边设计边打磨领域词汇表与决策记录(ADR) |
| `grilling` | `grilling-zh` | 访谈引擎（被 grill 系列技能内部调用） |
| `prototype` | `prototype-zh` | 生成可点按的逻辑/UI 原型 |
| `research` | `research-zh` | 派子代理做外部资料调研 |
| `resolving-merge-conflicts` | `resolving-merge-conflicts-zh` | 解决 Git 合并冲突 |
| `tdd` | `tdd-zh` | 测试驱动开发 |
| `wizard` | `wizard-zh` | 生成一步步引导填密钥/配置的交互向导 |
| `writing-for-agents` | `writing-for-agents-zh` | 给 agent 写文档的写法规范（被其它技能参考） |

### Matt Pocock 技能集 · 手动召唤（14 个，必须点名 `/技能名` 才跑）

| 英文 | 中文(-zh) | 一句话用途 | 你可以直接说的触发短语 |
|------|-----------|------------|------------------------|
| `ask-matt` | `ask-matt-zh` | 向 Matt Pocock "请教" TS/工程风格问题 | "ask matt…"、"Matt 会怎么写 X" |
| `grill-me` | `grill-me-zh` | 让 AI 严酷拷问你的想法/方案，找漏洞 | "拷问我"、"挑战一下我的方案" |
| `grill-with-docs` | `grill-with-docs-zh` | 同 grill-me，但边问边产出 ADR 和词汇表 | "边问边出文档" |
| `handoff` | `handoff-zh` | 把当前对话压缩成交接文档，给另一个 agent | "写个交接文档" |
| `implement` | `implement-zh` | 按规格说明或工单去实现代码 | "按这个 spec 实现" |
| `improve-codebase-architecture` | `improve-codebase-architecture-zh` | 扫描架构、找"加深模块"机会，出可视化报告 | "审查架构"、"找出浅模块" |
| `setup-matt-pocock-skills` | `setup-matt-pocock-skills-zh` | 为仓库一键配置工程类技能（issue 追踪器等） | "初始化技能配置" |
| `teach` | `teach-zh` | 多会话教学：系统地教你一个技能/概念 | "teach me X"、"教我…" |
| `to-questionnaire` | `to-questionnaire-zh` | 把答不清的决策变成问卷发给别人填 | "做个问卷" |
| `to-spec` | `to-spec-zh` | 把当前对话直接整理成规格说明 | "出个 spec"、"to spec" |
| `to-tickets` | `to-tickets-zh` | 把计划/规格拆成可独立开发的工单 | "拆工单"、"to tickets" |
| `triage` | `triage-zh` | 给 issues / 外部 PR 分诊（分类、核实、写简报） | "triage"、"分诊 #42" |
| `wait-what` | `wait-what-zh` | 用大白话重述你没看懂的那条消息 | "没看懂，重说" |
| `wayfinder` | `wayfinder-zh` | 把超大块工作规划成"决策工单地图"，逐个击破 | "规划这个大任务" |

---

## 六、目录结构（仓库长这样）

```
skills-collection/
├── README.md                 # 你正在看的说明
└── skills/                   # 所有技能都在这个文件夹里
    ├── extended-thinking/    # 【你自己的】扩展性思维技能
    ├── grill-me/             # Matt 技能 · 英文
    ├── grill-me-zh/          # Matt 技能 · 中文（带 -zh 后缀）
    ├── ...（其余 23 个 Matt 技能的中英两套）
    ├── mattpocock-menu/      # 导航技能 · 英文
    ├── mattpocock-menu-zh/   # 导航技能 · 中文
    └── （每个技能文件夹里：SKILL.md + 可能的 references/ 等）
```

约定：每个技能文件夹里的 `SKILL.md` 是**必须**的（元数据 + 指令），`references/`、`*.md`、`*.sh` 等是可选的参考资料。

---

## 七、常见问题（FAQ）

**Q1：英文版和中文版要都装吗？**
不用。二选一即可：想看原文装英文（原名），想看中文装 `-zh` 版。都装也行，只是占地方、名字不同不会冲突。

**Q2：装完没反应 / AI 不用这个技能？**
- 召唤型技能：确认你是**用 `/技能名` 点名**叫它的（自动型才不需要）。
- 通用：复制后重开一次 WorkBuddy。
- 确认文件夹直接放在 `~/.workbuddy/skills/` 下，且里面有 `SKILL.md`。

**Q3：技能之间会打架吗？**
不会。你自己的 `extended-thinking` 和 Matt 那套名字完全不同；Matt 的中英文靠 `-zh` 区分。WorkBuddy 按"文件夹名 + SKILL.md 里的 name 字段"识别，互不影响。

**Q4：我想只装其中几个，怎么挑？**
看上面"完整技能清单"，挑你用得上的那几行，把对应文件夹复制进 `skills/` 即可。新手从"导航 + grill-me-zh + to-spec-zh"三件套起步最稳。

**Q5：怎么更新到最新版？**
回到这个仓库 `git pull` 拉最新，再把 `skills/` 重新复制覆盖到本机 `skills/` 目录即可。

---

> 仓库维护约定：你自己的原创技能放 `skills/` 根下独立文件夹；第三方（如 Matt Pocock）技能保持原名，中文翻译统一加 `-zh` 后缀，避免与英文版重名。
