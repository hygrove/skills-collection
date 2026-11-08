---
name: ydfc
description: This skill should be used when the user requests a Python function for a YingDao RPA coding module by describing only its inputs and outputs, for example "传入XX，输出XX", optionally prefixed with 影刀模式 or 影刀模式 3.7：. It emits a single ready-to-paste code block that follows the fixed YingDao module skeleton, with every explanation carried by a detailed Chinese docstring and line-by-line comments. It never writes to or modifies YingDao project files.
---

# ydfc — 影刀编码模块函数生成器

## 用途

把「传入 X，输出 Y」这样一句自然语言描述，转换成一段可直接粘进影刀 RPA 编码版 Python 模块的代码。交付物只有代码：函数的全部说明写在 docstring 与逐行中文注释里，不另写独立说明书、不另写接入指引章节，不改写任何影刀工程文件。

## 触发与输入解析

- 识别显式技能调用，或句首出现「影刀模式」。模式词仅对当前这一句生效，不做会话常驻。
- 从描述中提取输入与输出。句式不标准时按语义宽松理解；信息缺失最多反问一句，不得连续追问。
- 版本号紧跟模式词时按该版本生成，例如 `影刀模式 3.7：传入…输出…`；未指定即按 Python 3.10.11。
- 需要影刀环境事实、调用机制或缺陷规避细节时，读取 `references/yingdao_rules.md`。

## 生成流程

1. 读取 `assets/skeleton.py.tpl`，以其为唯一骨架。
2. 在位置 A（4 行固定 import 之后、`def main` 之前）追加新增依赖；无依赖时保留一行中文注释说明「本函数只用自带功能，无需新增依赖」。
3. 保持注释块、4 行固定 import、`def main(args): pass` 逐字不变。
4. 在位置 B（`main` 之后）追加一个新函数，按「代码铁律」编写。
5. 输出**一个完整代码块**（骨架 + 新函数），便于整段复制；代码块之外最多写一句「用『调用模块』选函数 <函数名>」的提示。
6. 按「交付前自检清单」逐条核对后再输出。

## 代码铁律

- 标识符一律 ASCII，函数名用 `动词_名词` 并可加业务前缀；所有中文放进 docstring 与注释。
- 目标环境 Python 3.10.11，禁用 3.11+ 语法。签名可写基础注解（`: str`、`-> float`），不用 `X | Y`、复杂泛型或其他高级注解构造。
- 新函数用普通参数 + `return`；`args` 字典只属于 `main`，绝不混用。
- 默认纯函数：不读 `glv`、不调 `xbot`、不写文件、不产生副作用，除非用户当次明确要求。
- 默认参数不得使用列表、元组、字典；参数值避免内含逗号。
- 输入不合法时抛出带中文说明的异常；只包装可预判的错误，禁止宽泛 `except` 吞掉真实缺陷，禁止静默返回 `None`。
- 允许第三方包，但必须把装包步骤写进 docstring：影刀右侧「更多」→ 输入 pip 指令安装，且每个应用独立装包。
- 关键步骤逐行写中文注释，用大白话解释「这行在干嘛、为什么」，保证初学者能读懂。

## docstring 必备八项

在函数的 docstring 中依次写明：

1. 这个函数做什么（一句人话）
2. 输入（名字、类型、示例值）
3. 输出（类型、示例值）
4. 调用例子
5. 输入要求，以及不合法时的行为
6. 依赖与装包步骤
7. 运行环境（Python 版本）
8. 影刀里怎么调用（用「调用模块」指令选本函数名、设参数与返回值存储变量）

## 交付前自检清单

逐条核对，未通过不得输出：

- [ ] 语法合法，且不含 3.11+ 语法
- [ ] 骨架注释块、4 行固定 import、`main` 定义逐字未改
- [ ] 新增 import 只出现在位置 A，未覆盖 `from xbot import print`
- [ ] 新函数位于 `main` 之后，有 `return`，标识符为 ASCII
- [ ] 只使用基础注解，未出现 `X | Y` 或复杂泛型
- [ ] 无 `glv` / `xbot` 副作用，默认参数不是容器
- [ ] 错误分支抛中文异常，无宽泛 `except`、无静默 `None`
- [ ] docstring 八项齐全，关键步骤有逐行中文注释
- [ ] 未声称「已在影刀运行通过」
- [ ] 未写入或修改任何影刀工程文件

## 跨平台加载

本技能遵循 Agent Skills 开放规范：仅含 `SKILL.md`、`assets/`、`references/`，无脚本、无网络依赖、无 MCP 或厂商专有字段；frontmatter 只使用规范必需的 `name` 与 `description`。

- 安装：把整个 `ydfc/` 放进目标工具的技能搜索路径——WorkBuddy `~/.workbuddy/skills/`、Claude Code `.claude/skills/`、Cursor `.cursor/skills/`、Codex `.agents/skills/`、Gemini CLI `.gemini/skills/`。整目录复制，不要拆散 `assets/` 与 `references/`；正文对二者一律使用相对路径。
- 触发：各工具均按 `description` 做语义匹配，可直接说「影刀模式：传入…输出…」或「按 ydfc 规范写函数」。精确调用语法因工具而异（Claude Code `/ydfc`、Cursor `@` 或 `/`、Codex `$ydfc`、Gemini CLI `activate_skill`、WorkBuddy `@ydfc`）。
- 渐进加载：`description` 常驻、`SKILL.md` 命中时加载、`references/yingdao_rules.md` 按需读取。若目标工具不支持渐进加载，把 `assets/skeleton.py.tpl` 与 `references/yingdao_rules.md` 一并读入上下文即可。
- 迁移：本技能不写入任何影刀工程文件、不依赖本机绝对路径，换机器只需复制目录。若某平台的上传或打包校验要求额外字段，按该平台规范在 frontmatter 补充，不要改动正文规则。

## 资源

- `assets/skeleton.py.tpl`：影刀模块骨架，第 4 条注释按官方写「调用模块」。
- `references/yingdao_rules.md`：影刀环境、调用机制、已知缺陷与决策依据。
- 不附带校验脚本；自检以上述清单为准。
