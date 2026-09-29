# 超出范围知识库（Out-of-Scope Knowledge Base）

仓库里的 `.out-of-scope/` 目录，存储被拒绝功能请求的持久化记录。它有两个用途：

1. **机构记忆（Institutional memory）**：一个功能为何被拒，这样在 issue 关闭时推理不会丢失
2. **去重（Deduplication）**：当一个新 issue 进来、匹配先前的拒绝时，技能可以摆出先前的决策，而不是重新讨论它

## 目录结构（Directory structure）

```
.out-of-scope/
├── dark-mode.md
├── plugin-system.md
└── graphql-api.md
```

每个**概念**一个文件，而非每个 issue 一个。请求同一件事的多个 issue 被归到一个文件下。

## 文件格式（File format）

文件应当用一种轻松、可读的风格来写，更像一个简短的设计文档，而非一条数据库记录。用段落、代码示例和实例，让推理对第一次接触它的人清晰、有用。

```markdown
# Dark Mode

本项目不支持深色模式或面向用户的主题化。

## Why this is out of scope（为何超出范围）

渲染管线假定一个在 `ThemeConfig` 中定义的单一调色板。支持多主题将需要：

- 一个包裹整个组件树的主题 context provider
- 逐组件的主题感知样式解析
- 一个用于用户主题偏好的持久化层

这是一次重大的架构变更，与项目对内容创作的聚焦不一致。主题化是将输出嵌入或重新分发的下游消费者所关心的事。

```ts
// 当前的 ThemeConfig 接口并非为运行时切换而设计：
interface ThemeConfig {
  colors: ColorPalette; // 单一调色板，构建时解析
  fonts: FontStack;
}
```

## Prior requests（先前的请求）

- #42: "Add dark mode support"
- #87: "Night theme for accessibility"
- #134: "Dark theme option"
```

### 命名文件（Naming the file）

用简短、描述性的 kebab-case 名称命名概念：`dark-mode.md`、`plugin-system.md`、`graphql-api.md`。名称应当足够可辨认，让某人浏览目录时无需打开文件就能理解被拒的是什么。

### 撰写理由（Writing the reason）

理由应当有实质：不是"我们不想要这个"，而是为什么。好的理由引用：

- 项目范围或哲学（"本项目聚焦 X；主题化是下游的事"）
- 技术约束（"支持这个会需要 Y，而那与我们的 Z 架构冲突"）
- 战略决策（"我们因为……而选了 A 而非 B"）

理由应当耐久。避免引用临时情况（"我们现在太忙了"）；那些不是真正的拒绝，它们是推迟。

## 何时检查 `.out-of-scope/`（When to check `.out-of-scope/`）

在分诊期间（第 1 步：收集上下文），读取 `.out-of-scope/` 里的所有文件。当评估一个新 issue 时：

- 检查请求是否匹配一个现有的超出范围概念
- 匹配是按概念相似度，而非关键词："night theme" 匹配 `dark-mode.md`
- 如果有匹配，把它摆给维护者："这与 `.out-of-scope/dark-mode.md` 相似。我们之前因为它的理由而拒绝了它。你还这么觉得吗？"

维护者可能：

- **确认（Confirm）**：新 issue 被追加到现有文件的 "Prior requests" 列表，然后关闭
- **重新考虑（Reconsider）**：超出范围文件被删除或更新，issue 走正常分诊
- **不同意（Disagree）**：issues 相关但不同，走正常分诊

## 何时写入 `.out-of-scope/`（When to write to `.out-of-scope/`）

仅当一个 **enhancement**（不是 bug）被作为 `wontfix` *拒绝*时。这也同样适用于 enhancement 的 PR：一个被拒的 PR 被记录在这里，这样同样的请求不会作为新代码回来。

当某物因为**已经实现**而被作为 `wontfix` 关闭时，绝**不要**写到这里。那是已构建的功能，不是被拒的；记录它会用虚假的拒绝污染去重检查。相反，关闭评论指向功能已经存在的位置。

流程：

1. 维护者决定一个功能请求超出范围
2. 检查是否已有匹配的 `.out-of-scope/` 文件
3. 如果有：把新 issue 追加到 "Prior requests" 列表
4. 如果没有：以概念名、决策、理由和第一条先前请求创建一个新文件
5. 在 issue 上发一条评论，解释决策并提及 `.out-of-scope/` 文件
6. 用 `wontfix` 标签关闭 issue

## 更新或移除超出范围文件（Updating or removing out-of-scope files）

如果维护者改变了对先前被拒概念的想法：

- 删除 `.out-of-scope/` 文件
- 技能无需重开旧 issue；它们是历史记录
- 触发重新考虑的这次新 issue 走正常分诊
