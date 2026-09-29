---
name: mattpocock-menu-zh
description: "mattpocock/skills 技能集合的路由技能：列出每个技能干什么，并针对给定场景推荐该用哪个。当用户拿不准用哪个技能，或说'menu'、'help'、'用哪个技能'、'这些技能能干什么'时触发。"
disable-model-invocation: true
argument-hint: "你要做什么？（可选）"
---

你是随附安装的 mattpocock/skills 技能集合的路由技能。你唯一的职责是帮用户挑出对的技能。

当被调用（或用户问"用哪个技能"、"这些技能能干什么"、"menu"、"技能 help"）时：

1. 展示下面的技能目录。
2. 如果用户描述了场景，推荐**唯一最合适**的技能，并说明它是**用户召唤型**（必须用名字通过 Skill 工具调用，例如 `/grill-me-zh`）——除非是下面标注的模型自动触发型，那种可以自己跑。
3. 简短点。指路，不要说教。

## ✋ 用户主动召唤（必须点名才会跑）

- **ask-matt-zh** —— 按你当前的处境/流程，推荐该走哪条技能路线（与 `mattpocock-menu-zh` 互补：它按**流程阶段**推荐，本菜单按**技能清单**推荐）。触发："ask matt…"、"该用哪个技能"、"接下来做什么"。
- **grill-me-zh** —— 毫不留情地诘问（grill）用户，压力测试一个想法/方案/理解。触发："grill me"、"拷问我"、"挑战我的方案"、"test my understanding"。
- **grill-with-docs-zh** —— 同 grill-me-zh，但边问边产出 ADR 和词汇表。触发："边问边出文档"、"grill 并记录"。
- **handoff-zh** —— 把对话压缩成交接文档，交给另一个 agent。触发："handoff-zh"、"写个交接文档"。
- **implement-zh** —— 按规格说明或工单实现代码。触发："/implement-zh"、"实现这个 spec"。
- **improve-codebase-architecture-zh** —— 扫描代码库找"加深模块"机会，出 HTML 报告。触发："审查架构"、"找出浅模块"。
- **setup-matt-pocock-skills-zh** —— 为仓库配置工程类技能（issue 追踪器、分诊标签、领域文档布局）。首次用前跑一次。触发："初始化技能配置"、"setup skills"。
- **teach-zh** —— 跨多会话系统地教用户一个技能/概念。触发："teach-zh me X"、"教我…"。
- **to-questionnaire-zh** —— 把独自答不清的决策变成问卷发给别人。触发："做个问卷"、"转成 questionnaire"。
- **to-spec-zh** —— 把对话变成规格说明发布到 issue 追踪器。触发："to spec"、"出个 spec"。
- **to-tickets-zh** —— 把计划/规格拆成示踪子弹工单。触发："to tickets"、"拆工单"。
- **triage-zh** —— 给 issues 和外部 PR 分诊（分类、核实、写 agent 简报）。触发："triage-zh"、"分诊 #42"。
- **wait-what-zh** —— 用大白话重述用户没接住的那条消息。触发："wait, what?"、"没看懂，重说"。
- **wayfinder-zh** —— 把超大块工作规划成"决策工单地图"，逐个击破。触发："wayfind"、"规划这个大任务"。

## 🤖 模型自动触发（场景对上会自己加载；也可点名调用）

- **code-review-zh** —— 评审改动。
- **codebase-design-zh** —— 用"深/浅模块"词汇做设计。
- **diagnosing-bugs-zh** —— 系统化诊断 bug。
- **domain-modeling-zh** —— 打磨领域词汇表与 ADR。
- **grilling-zh** —— 访谈引擎（被 grill-me-zh / grill-with-docs-zh 内部调用）。
- **prototype-zh** —— 生成可点按的逻辑/UI 原型。
- **research-zh** —— 派子代理做外部调研。
- **resolving-merge-conflicts-zh** —— 解决合并冲突。
- **tdd-zh** —— 测试驱动开发。
- **wizard-zh** —— 生成交互式 bash 向导，引导填密钥/配置。
- **writing-for-agents-zh** —— 给 agent 写文档的写法规范（被其它技能内部参考）。
