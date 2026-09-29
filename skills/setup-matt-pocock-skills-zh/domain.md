# 领域文档（Domain Docs）

工程类技能在探索代码库时，应当如何消费本仓库的领域文档。

## 探索之前，先读这些

- 仓库根目录的 **`CONTEXT.md`**，或
- 若根目录存在 **`CONTEXT-MAP.md`**：它指向每个上下文一个 `CONTEXT.md`。读每一个与话题相关的。
- **`docs/adr/`**：读触及你即将工作的区域的 ADR。在多上下文仓库里，也检查 `src/<context>/docs/adr/` 里上下文范围的决策。

如果这些文件任何一个不存在，**静默继续**。不要标记它们缺失；不要建议预先创建它们。`/domain-modeling` 技能（经由 `/grill-with-docs` 与 `/improve-codebase-architecture` 抵达）会在术语或决策真正被解决时惰性创建它们。

## 文件结构

单上下文仓库（大多数仓库）：

```
/
├── CONTEXT.md
├── docs/adr/
│   ├── 0001-event-sourced-orders.md
│   └── 0002-postgres-for-write-model.md
└── src/
```

多上下文仓库（根目录存在 `CONTEXT-MAP.md`）：

```
/
├── CONTEXT-MAP.md
├── docs/adr/                          ← 系统级决策
└── src/
    ├── ordering/
    │   ├── CONTEXT.md
    │   └── docs/adr/                  ← 上下文范围的决策
    └── billing/
        ├── CONTEXT.md
        └── docs/adr/
```

## 使用词汇表的词汇

当你的输出命名一个领域概念时（在 issue 标题、重构提议、假设、测试名里），使用 `CONTEXT.md` 里定义的术语。不要漂移到词汇表明确避免的同义词。

如果你需要的概念还不在词汇表里，那是个信号：要么你在发明项目不用的语言（重新考虑），要么确实存在一个真实的缺口（为 `/domain-modeling` 记下它）。

## 标记 ADR 冲突

如果你的输出与某个现有 ADR 相矛盾，显式地把它摆出来，而不是静默覆盖：

> _Contradicts ADR-0007 (event-sourced orders), but worth reopening because…_（与 ADR-0007（事件溯源订单）相矛盾，但值得重开，因为……）
