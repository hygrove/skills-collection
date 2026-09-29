# HTML 报告格式（HTML Report Format）

架构评审被渲染成操作系统临时目录里一份自包含的 HTML 文件。Tailwind 与 Mermaid 都来自 CDN。Mermaid 可靠地处理图状（graph-shaped）图表；手工打造的 div 与内联 SVG 处理更有"编辑感"的视觉（质量图、剖面图）。两者混用：别什么都靠 Mermaid，否则会开始显得千篇一律。

## 骨架（Scaffold）

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <title>Architecture review for {{repo name}}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script type="module">
      import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
      mermaid.initialize({ startOnLoad: true, theme: "neutral", securityLevel: "loose" });
    </script>
    <style>
      /* 给 Tailwind 覆盖不到的细处加的小自定义层：
         虚线接缝、手绘感的箭头头等。 */
      .seam { stroke-dasharray: 4 4; }
      .leak { stroke: #dc2626; }
      .deep { background: linear-gradient(135deg, #0f172a, #1e293b); }
    </style>
  </head>
  <body class="bg-stone-50 text-slate-900 font-sans">
    <main class="max-w-5xl mx-auto px-6 py-12 space-y-12">
      <header>...</header>
      <section id="candidates" class="space-y-10">...</section>
      <section id="top-recommendation">...</section>
    </main>
  </body>
</html>
```

## 页眉（Header）

仓库名、日期，以及一段紧凑的图例：实心框 = 模块，虚线 = 接缝，红色箭头 = 泄漏，深色的粗框 = 深模块。不要引言段落。直接进入候选方案。

## 候选卡片（Candidate card）

图表演重头戏。散文稀疏、平实，不事修饰地使用词汇表术语（来自 `/codebase-design` 技能）。

每个候选方案是一个 `<article>`：

- **标题（Title）**：简短，点出加深动作（如"Collapse the Order intake pipeline"→"合并订单受理管线"）。
- **徽章行（Badge row）**：推荐强度（`Strong` 翠绿、`Worth exploring` 琥珀、`Speculative` 石板灰），外加一个依赖类别标签（`in-process`、`local-substitutable`、`ports & adapters`、`mock`）。
- **文件（Files）**：等宽字体列表，`font-mono text-sm`。
- **前后对比图（Before / After diagram）**：核心。两栏并排。见下方模式。
- **问题（Problem）**：一句话。哪里疼。
- **解决方案（Solution）**：一句话。改变什么。
- **收益（Wins）**：要点，每条 ≤6 个词。如"Tests hit one interface""Pricing logic stops leaking""Delete 4 shallow wrappers"。
- **ADR 提示框（ADR callout）**（如适用）：琥珀色框里一行。

不要解释性段落。如果一张图需要一段文字才看得懂，就重画这张图。

## 图样模式（Diagram patterns）

挑契合候选方案的模式。混用它们。别让每张图都长一个样。多样化本身就是重点的一部分。

### Mermaid 图（依赖 / 调用流的常备工具）

当要表达的是"X 调 Y 调 Z，看看这团乱麻"时，用 Mermaid 的 `flowchart` 或 `graph`。把它包进一个 Tailwind 样式的卡片，免得像是被空投进来的。用 classDef 把泄漏的边染红、把深模块染深。时序图很适合表现"之前：6 次往返；之后：1 次"。

```html
<div class="rounded-lg border border-slate-200 bg-white p-4">
  <pre class="mermaid">
    flowchart LR
      A[OrderHandler] --> B[OrderValidator]
      B --> C[OrderRepo]
      C -.leak.-> D[PricingClient]
      classDef leak stroke:#dc2626,stroke-width:2px;
      class C,D leak
  </pre>
</div>
```

### 手工盒子加箭头（当 Mermaid 的布局跟你作对时）

模块用带边框和标签的 `<div>`。箭头用内联 SVG `<line>` 或 `<path>` 元素，绝对定位在一个相对容器之上。当你想要"之后"的图呈现为一个粗边框深模块、内部灰化时，就伸手用这个，因为 Mermaid 渲染不出那种分量。

### 剖面图（适合分层式的浅）

堆叠水平条带（`h-12 border-l-4`）来展示一次调用穿过的各层。之前：6 条各无所作为的薄层。之后：1 条粗带，标着合并后的职责。

### 质量图（适合"接口和实现对等宽"）

每个模块两个矩形：一个代表接口表面积，一个代表实现。之前：接口矩形几乎和实现矩形一样高（浅）。之后：接口矩形矮，实现矩形高（深）。

### 调用图坍缩（Call-graph collapse）

之前：一棵函数调用树，渲染成嵌套盒子。之后：同一棵树坍缩进一个盒子，原先内部的调用在它内部以淡色显示。

## 样式指引（Style guidance）

- 偏编辑感，而非企业仪表盘。留白充裕。标题可用衬线（serif 配 stone/slate 不错）。
- 省着用色：一个强调色（翠绿或靛蓝）外加红色表泄漏、琥珀色表警告。
- 图保持约 320px 高，好让前后对比舒适并排、无需滚动。
- 图内模块标签用 `text-xs uppercase tracking-wider`，让它们读起来像示意图，而非 UI。
- 唯一的脚本是 Tailwind CDN 和 Mermaid ESM 导入。报告其它部分都是静态的：没有应用代码，除 Mermaid 自身渲染外没有交互。

## 首要推荐区（Top recommendation section）

一张更大的卡片。候选名、一句为什么、到它卡片的锚点链接。就这些。

## 语气（Tone）

平实的英文、简洁，但架构名词和动词直接来自 `/codebase-design` 技能。简洁不是漂移到其它说法的借口。

**精确使用：** module、interface、implementation、depth、deep、shallow、seam、adapter、leverage、locality。

**绝不替换：** component、service、unit（代 module）· API、signature（代 interface）· boundary（代 seam）· layer、wrapper（代 module，当你意指 module 时）。

**贴合风格的措辞：**

- "Order intake module is shallow: interface nearly matches the implementation."（订单受理模块很浅：接口几乎和实现对等。）
- "Pricing leaks across the seam."（定价跨接缝泄漏。）
- "Deepen: one interface, one place to test."（加深：一个接口，一个测试点。）
- "Two adapters justify the seam: HTTP in prod, in-memory in tests."（两个适配器证明了接缝的正当性：生产用 HTTP，测试用内存。）

**收益要点**用词汇表术语点出收益：*"locality: bugs concentrate in one module"*、*"leverage: one interface, N call sites"*、*"interface shrinks; implementation absorbs the wrappers"*。不要写 *"easier to maintain"* 或 *"cleaner code"*，因为这些词不在词汇表里，不配占位。

不要含糊其辞、不要清嗓子、不要"值得一提的是……"。如果一句话能变成要点，就把它变成要点。如果一个要点可被删掉，就删掉它。如果一个术语不在 `/codebase-design` 词汇表里，在发明新词之前先去够一个已有的。
