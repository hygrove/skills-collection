# CONTEXT.md 格式（CONTEXT.md Format）

## 结构

```md
# {上下文名称}

{一两句话描述这个上下文是什么、为何存在。}

## Language 语言

**Order 订单**：
{对该术语的一两句描述}
_避免（Avoid）_：Purchase、transaction

**Invoice 发票**：
交付后发给客户的一份付款请求。
_避免（Avoid）_：Bill、payment request

**Customer 客户**：
下单的个人或组织。
_避免（Avoid）_：Client、buyer、account
```

## 规则

- **要有主见。** 当同一个概念有多个词时，挑最好的那个，把其余列在 `_Avoid_` 下。
- **定义要收紧。** 最多一两句话。定义它*是什么*，而不是它做什么。
- **只收录专属于本项目上下文的术语。** 通用的编程概念（超时、错误类型、工具模式）即便项目大量使用也不属于这里。在添加一个术语前先问：这是一个独有于此上下文的概念，还是一个通用编程概念？只有前者才属于。
- **当自然聚类出现时，把术语归在子标题下。** 如果所有术语都属于一个内聚区域，扁平列表也行。

## 单上下文 vs 多上下文仓库

**单上下文（大多数仓库）：** 仓库根目录一个 `CONTEXT.md`。

**多上下文：** 仓库根目录一个 `CONTEXT-MAP.md`，列出各个上下文、它们位于何处、以及彼此如何关联：

```md
# Context Map 上下文地图

## Contexts 上下文

- [Ordering 订单](./src/ordering/CONTEXT.md)：接收并跟踪客户订单
- [Billing 账单](./src/billing/CONTEXT.md)：生成发票并处理付款
- [Fulfillment 履约](./src/fulfillment/CONTEXT.md)：管理仓库拣货与发货

## Relationships 关系

- **Ordering → Fulfillment**：Ordering 发出 `OrderPlaced` 事件；Fulfillment 消费它们以开始拣货
- **Fulfillment → Billing**：Fulfillment 发出 `ShipmentDispatched` 事件；Billing 消费它们以生成发票
- **Ordering ↔ Billing**：`CustomerId` 与 `Money` 的共享类型
```

技能推断适用哪种结构：

- 若 `CONTEXT-MAP.md` 存在，读它来找上下文
- 若只有根 `CONTEXT.md` 存在，则是单上下文
- 若两者都不存在，在第一个术语被解决时惰性创建根 `CONTEXT.md`

当存在多个上下文时，推断当前话题与哪一个相关。若不清楚，就问。
