# 技能机制（Skill mechanics）

[`writing-for-agents-zh`](SKILL.md) 中技能专属的分支：当文档是一个技能时（frontmatter、调用选择、路由型技能）有什么变化。关于写它的其它一切，都是 `SKILL.md` 里的通用参考。

## 调用（Invocation）

两个选择，交换两种负载：

- 一个 **model-invoked（模型召唤）** 技能保留一个 `description`，于是 agent 能自主触发它，其它技能也能抵达它。你仍然可以键入它的名字：模型召唤永远*包含*人类可达性；一个 description 只会增添 agent 的发现能力，绝不会移除人类的。这个 description 是技能顶层的上下文指针，被迫始终保持在加载状态：以永久的上下文负载，换取可发现性。一个内容全为参考的 model-invoked 技能，也是共享参考的一个家：另一个技能可以调用它，于是多个技能需要的参考住在同一个地方。机制：省略 `disable-model-invocation`，并写一个面向模型、承载触发分支的 description（`SKILL.md` 里的指针书写规则完整适用）。
- 一个 **user-invoked（用户召唤）** 技能把 description 从 agent 的可达范围里剥掉：只有键入其名的人类能调用它，且其它技能都不能。零上下文负载，但它花费认知负载：你就是那个必须记住它存在的索引。机制：设置 `disable-model-invocation: true`；`description` 变成面向人类的：一句话摘要，触发列表被剥离。

只有当 agent 必须自己抵达技能，或其它技能必须抵达时，才选 model-invocation。如果它永远只靠手触发，就让它 user-invoked，不付任何上下文负载。

两个 user-invoked 技能都需要的共享参考，无法住在任一者里：没有 description，谁都无法触发另一个。把它推到一个技能系统之外的纯文件：任何技能都能指向的外部参考。

## 按调用拆分（Splitting by invocation）

拆分的调用切口（序列切口住在 `SKILL.md` 里）：当你有一个应当独自触发它的、独特的首词（你在提示词里真正用到的一个触发词），或其它技能必须抵达它时，拆出一个 model-invoked 技能。你为那个新的始终加载的 description 付出上下文负载，所以那种独立可达性必须值得。

## 路由型技能（Router skills）

当 user-invoked 技能多到超出你能记住的范围时，那堆积的认知负载被一个**路由型技能（router skill）**治愈：一个 user-invoked 技能，点名其它技能、以及何时去够每一个，这样人类只需记住一个技能，而非许多个。它只能暗示，永远无法触发它们：user-invoked 技能没有 description，所以除了人类谁都无法抵达它们。
