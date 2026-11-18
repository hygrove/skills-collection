---
name: ydfc
description: Generate a ready-to-paste Python function for a YingDao (影刀) RPA coding module from a plain-language spec like "传入XX，输出XX", optionally prefixed with 影刀模式 or 影刀模式 3.7：. When the request is ambiguous, it first runs one round of structured questions (AskUserQuestion) to settle the decisions, while looking up facts itself. The result is one complete code block following the fixed YingDao module skeleton, with all explanation carried by a concise Chinese docstring and inline comments. The function is executed and asserted against real inputs in a local Python environment before delivery, and the exact bytes verified are the bytes pasted to the user — YingDao is only a packaging shell, the function body is ordinary Python. Keep the code lean: no speculative branches, no defensive dead paths, docstring items of 1-3 lines each. It never writes to YingDao project files.
---

# ydfc — 影刀编码模块函数生成器

把「传入 X，输出 Y」这句自然语言，变成一段能直接粘进影刀 RPA 编码模块的 Python 代码。

**影刀只是外壳。** 骨架里的 `xbot` / `package` / `main(args)` 是影刀注入的壳；真正被交付和执行的是位置 B 的新函数，它就是普通 Python。所以"本机没有 xbot"从不是跳过运行验证的理由——把壳剥掉，用普通 Python + 真实输入跑通即可。

## 触发与输入解析

- 识别显式技能调用，或句首出现「影刀模式」。模式词仅对当前这一句生效。
- 从描述中提取输入与输出。句式不标准时按语义宽松理解。
- 版本号紧跟模式词时按该版本生成（`影刀模式 3.7：`）；未指定即用 references 里「运行环境」一节给的目标版本。

## 需求模糊时的访谈

需求含糊时，先发一轮访谈再写代码。用 `AskUserQuestion` 工具发布选择题（自带"其他"输入框，用户可自由作答）。问题怎么写、典型决策点见 references「需求模糊时的访谈细则」。

**判据**：先自己查一轮 —— **事实归你，决策归用户**。文件里有什么列、依赖装没装，你自己查；取哪个口径、异常怎么处理、输出什么形态，发访谈问用户。

满足**任一条**即发：同一需求有两种以上合理实现且选错会返工；关键参数缺失（源文件位置、目标指标、口径定义）；用户用了"大概""随便""看着办"这类词。

**不发**：需求已能唯一确定实现；或缺的信息你查一下就有。

**发法**：一次最多 4 问，一次问完不分轮。每题 2-4 个选项（写成 `{label, description}` 对象，不是纯字符串），第一个是推荐项并标 `（推荐）`，description 写清各选项代价。

**发完**：用户选完 → 立刻按选择继续，不二次确认；没选或答"随便" → 按推荐项继续，交付时一句话说明假设；选了推荐项以外的内容 → 按用户的选择做，不加自己的偏好。

*完成标准：一轮访谈足够定下所有决策；剩下的都是事实，你查得到。*

## 生成流程

按顺序执行。每步都给出完成标准——达到即进入下一步。

**第 0 步 · 查事实，必要时访谈**
先自己查事实：读用户提到的文件、探列名、确认依赖。查出需求已唯一确定 → 直接进第 1 步。
仍有决策悬空 → 按「需求模糊时的访谈」发一轮，问完即进第 1 步。
*完成标准：所有决策已由用户拍板或按推荐项默认；所有事实你已查到。*

**第 1 步 · 搭骨架**
读 `assets/skeleton.py.tpl`，以此为唯一骨架。在位置 A（4 行固定 import 之后、`def main` 之前）追加新依赖；无依赖就留一行中文注释说明「本函数只用自带功能，无需新增依赖」。
*完成标准：4 行固定 import、注释块、`def main(args): pass` 与模板逐字一致。*

**第 2 步 · 写函数**
在位置 B（`main` 之后）追加一个新函数。规则见 `references/yingdao_rules.md`——代码铁律、docstring 八项、简洁性要求、影刀环境事实都在那里。
*完成标准：函数符合 references 的代码铁律与 docstring 八项（门禁脚本会自动核对其中大部分）。*

**第 3 步 · 落盘**
把完整模块（骨架 + 新函数）写成一个临时 `.py`，UTF-8。
*完成标准：文件存在，且这就是你即将交付的那份内容。*

**第 4 步 · 跑门禁（强制）**
```bash
python ~/.workbuddy/skills/ydfc/assets/verify_gate.py <模块文件.py> [断言脚本.py]
```
门禁自动完成三道：语法 + 3.10 兼容 + 转义体检；骨架完整性 + import 位置 + 签名 + 纯函数 + docstring；剥离壳后实跑并校验通用契约（正反斜杠等价、非法输入抛明确异常）。

第二个参数是可选的针对性断言脚本，写你自己的 `assert`（如"销售额必须等于 1317.8"）。门禁内的实跑脚本会把 `f`（被测函数）注入断言脚本的命名空间。

涉及文件读写的任务，先设 `YDFC_TEST_XLSX` 指向用户的真实文件再跑，正反斜杠等价性检查会启用。

*完成标准：门禁三道全绿。任何一项 FAIL 都先改代码再重跑。*

**第 5 步 · 交付**
用 Read 读回第 3 步那个文件，**逐字**贴成一个完整代码块。代码块外最多写一句「用『调用模块』选函数 <函数名>」。
*完成标准：贴出的每个字符都来自被验证的那份文件。*

## 两条铁律

**铁律一：被验证的字节必须就是交付的字节。**
第 3 步写盘 → 对这个文件验证 → 第 5 步用 Read 读回逐字粘贴。链路只有一条，中间不重新生成、不重新手敲。
若你打算在聊天里现写一段代码贴给用户，用 `verify_gate.py --text <文本文件>` 先验那段文本本身。

**铁律二：交付物必须真的能跑通。**
唯一证据是：用真实输入执行它、打印实际输出、断言比对通过。"逻辑是对的""我读过了"都不算。

## 转义与反斜杠

Windows 路径是字符串字面量的头号杀手：`\U` 会被当成 Unicode 转义的开头（要求后跟 8 位十六进制），报 `truncated \UXXXXXXXX escape`。

- **路径写正斜杠**：`"C:/Users/admin/Desktop/x.xlsx"`。Windows 下完全等价。
- **必须写反斜杠时用 `chr(92)`**，避免源码里的反斜杠在转贴时被改写。
- **docstring 里的 `r"..."` 陷阱**：那个 `r` 只是给人看的文本。docstring 自身若不是以 `r"""` 开头，里面的 `\U` 照样报错；而 `r"""` 内部不能再出现 `"""`，否则 docstring 提前截断。
- 影刀「调用模块」参数面板里手填的路径同样会变成字符串字面量，面板里用正斜杠最稳。

## 交付时可声称的边界

- 可以说："已在普通 Python 环境用真实输入实跑通过，输出为 XXX。"
- 影刀内的注入与调度未经验证，交付声明里不出现「已在影刀运行通过」。
- 若函数确实依赖 xbot 运行时（本机无法实跑），明确说明这一点与原因。
- 交付物只有代码文本。影刀工程文件的写入限制见 references「工程文件写入」一节。

## 交付前自检清单

逐条核对，未通过不输出。规则的定义在 `references/yingdao_rules.md`，这里只列检查动作。

**需求澄清**
- [ ] 有悬空决策时已发过访谈（AskUserQuestion），且是一轮问完
- [ ] 问的是决策而非事实——事实已自己查过
- [ ] 每个问题的第一个选项是推荐项并标注 `（推荐）`
- [ ] 需求已唯一确定时没有多余访谈

**一致性**
- [ ] 贴出的代码块逐字来自被验证的那份文件（Read 读回后粘贴）
- [ ] 交付文本的语法已用 `ast.parse()` 确认

**语法与兼容**
- [ ] `ast.parse(src, feature_version=(3,10))` 通过
- [ ] 无歧义转义（反斜杠 + 大写 U / 大写 x 需在 raw 字符串内），Windows 路径用正斜杠

**结构**
- [ ] 骨架注释块、4 行固定 import、`main` 定义逐字未改
- [ ] 新增 import 只出现在位置 A
- [ ] 门禁报告的签名项全绿（return / 标识符 / 注解 / 默认参数 / 纯函数 / 中文异常）

**可运行性**
- [ ] 门禁三道全绿，实跑输出有断言通过的实际结果
- [ ] 覆盖正常输入 + 边界输入 + 非法输入三类

**简洁性**
- [ ] 门禁的 docstring 行数检查通过（未喧宾夺主）
- [ ] 没有为假想需求写的分支和多余参数
- [ ] 注释解释"为什么"而非复述"做什么"

**边界**
- [ ] 交付声明与实际验证范围一致
- [ ] 未写入或修改任何影刀工程文件

## 资源

- `assets/skeleton.py.tpl` — 模块骨架，第 4 条注释按官方写「调用模块」。
- `assets/verify_gate.py` — 交付门禁。`python verify_gate.py <模块文件.py> [断言脚本.py]`；涉及文件读写时设 `YDFC_TEST_XLSX` 指向真实 xlsx；`--text <文件>` 验证一段交付文本本身。
- `assets/verify_gate_selftest.py` — 门禁自身的反向测试。`python verify_gate_selftest.py <一份合格模块>` 会造出 13 类坏代码，确认门禁都能抓到。一个只会报 PASS 的门禁等于没有门禁。
- `references/yingdao_rules.md` — 代码铁律、docstring 八项、简洁性要求、影刀环境与调用机制、已知缺陷。

## 跨平台加载

本技能遵循 Agent Skills 开放规范：仅含 `SKILL.md`、`assets/`、`references/`，无网络依赖、无 MCP 或厂商专有字段；frontmatter 只用规范必需的 `name` 与 `description`。

- 安装：把整个 `ydfc/` 放进目标工具的技能搜索路径——WorkBuddy `~/.workbuddy/skills/`、Claude Code `.claude/skills/`、Cursor `.cursor/skills/`、Codex `.agents/skills/`、Gemini CLI `activate_skill`。整目录复制，不要拆散 `assets/` 与 `references/`。
- 触发：各工具按 `description` 语义匹配，可直接说「影刀模式：传入…输出…」或「按 ydfc 规范写函数」。
- 迁移：本技能不依赖本机绝对路径，换机器只需复制目录。
