# skills-collection

WorkBuddy 全局 skill 收集仓库。把跨机器、跨项目可复用的 skill 集中在这里，方便在异地直接拉取使用。

## 已收录

| Skill | 说明 |
|-------|------|
| `skills/extended-thinking` | 扩展性思维回答（合并版）：四段合同「核心答案 → 🔗 关联扩展 → ⚠️ 避坑指南 → 🛠 真实坑」，含联想引擎五步法与按领域预置的素材库；真实坑禁止编造第一人称经历。 |

## 安装到本机

把 `skills/` 下对应的技能目录，整个复制到 WorkBuddy 的全局 skill 目录即可（复制或软链均可）：

```bash
# Windows（PowerShell / Git Bash）
cp -r skills/extended-thinking "$HOME/.workbuddy/skills/"

# macOS / Linux
cp -r skills/extended-thinking ~/.workbuddy/skills/

# Qoder（用户级全局目录）
cp -r skills/extended-thinking "$HOME/.qoder-cn/skills/"
```

复制后 WorkBuddy 无需重启，下一轮对话即生效（会自动发现 `~/.workbuddy/skills/` 下的技能）；Qoder 需重启会话或执行 `/skills reload`。

## 目录约定

```
skills-collection/
├── README.md
└── skills/
    └── <skill-name>/
        ├── SKILL.md          # 必须：元数据 + 指令
        └── references/       # 可选：参考资料
```
