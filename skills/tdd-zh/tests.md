# 好测试与坏测试（Good and Bad Tests）

## 好测试（Good Tests）

**集成风格（Integration-style）**：通过真实接口测试，而不是对内部各部分的 mock。

```typescript
// 好：测试可观察的行为
test("user can checkout with valid cart", async () => {
  const cart = createCart();
  cart.add(product);
  const result = await checkout(cart, paymentMethod);
  expect(result.status).toBe("confirmed");
});
```

特征：

- 测试用户/调用方在乎的行为
- 只用公共 API
- 能在内部重构后存活
- 描述 WHAT（是什么），而非 HOW（怎么做）
- 每个测试一个逻辑断言

## 坏测试（Bad Tests）

**实现细节测试（Implementation-detail tests）**：与内部结构耦合。

```typescript
// 坏：测试实现细节
test("checkout calls paymentService.process", async () => {
  const mockPayment = jest.mock(paymentService);
  await checkout(cart, payment);
  expect(mockPayment.process).toHaveBeenCalledWith(cart.total);
});
```

危险信号：

- mock 内部协作者
- 测试私有方法
- 断言调用次数 / 顺序
- 重构（行为未变）时测试就坏
- 测试名描述 HOW 而非 WHAT
- 绕开接口、通过外部手段验证

```typescript
// 坏：绕开接口来验证
test("createUser saves to database", async () => {
  await createUser({ name: "Alice" });
  const row = await db.query("SELECT * FROM users WHERE name = ?", ["Alice"]);
  expect(row).toBeDefined();
});

// 好：通过接口验证
test("createUser makes user retrievable", async () => {
  const user = await createUser({ name: "Alice" });
  const retrieved = await getUser(user.id);
  expect(retrieved.name).toBe("Alice");
});
```

**同义反复测试（Tautological tests）**：期望值把实现又算了一遍，于是测试靠构造本身就能通过。

```typescript
// 坏：期望值按代码计算的方式重新计算
test("calculateTotal sums line items", () => {
  const items = [{ price: 10 }, { price: 5 }];
  const expected = items.reduce((sum, i) => sum + i.price, 0);
  expect(calculateTotal(items)).toBe(expected);
});

// 好：期望值是一个独立的、已知的字面量
test("calculateTotal sums line items", () => {
  expect(calculateTotal([{ price: 10 }, { price: 5 }])).toBe(15);
});
```
