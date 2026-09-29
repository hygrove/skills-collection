---
name: handoff-zh
description: 把当前对话压缩成一份交接文档，供另一个 agent 接手。
argument-hint: "下一个会话将用来做什么？"
disable-model-invocation: true
---

写一份交接文档，总结当前对话，好让一个全新的 agent 能继续这项工作。保存到用户操作系统的临时目录——而不是当前工作区。

在文档中包含一个"suggested skills 建议技能"小节，点名下一个 agent 应当调用 Skill 工具的那些技能。

不要重复其它产物（规格说明、计划、ADR、issues、提交、diff）里已捕获的内容。改为按路径或 URL 引用它们。

编辑掉任何敏感信息，例如 API 密钥、密码，或个人身份信息。

如果用户传入了参数，把它们当作对下一个会话将聚焦什么的描述，并据此裁剪文档。
