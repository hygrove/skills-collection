# skills-collection

WorkBuddy 全局 skill 收集仓库。把跨机器、跨项目可复用的 skill 集中在这里，方便在异地直接拉取使用。

## 已收录

| Skill | 说明 |
|-------|------|
| `skills/expansive-thinking` | 扩展性思维回答：每次回答围绕主题补充 1-2 个紧密相关的延伸知识，并固定给出「⚠️ 避坑指南」与「🛠 真实项目中的坑」。 |

## 安装到本机

把 `skills/` 下对应的技能目录，整个复制到 WorkBuddy 的全局 skill 目录即可（复制或软链均可）：

```bash
# Windows（PowerShell / Git Bash）
cp -r skills/expansive-thinking "$HOME/.workbuddy/skills/"

# macOS / Linux
cp -r skills/expansive-thinking ~/.workbuddy/skills/
```

复制后无需重启，下一轮对话即生效（WorkBuddy 会自动发现 `~/.workbuddy/skills/` 下的技能）。

## 目录约定

```
skills-collection/
├── README.md
└── skills/
    └── <skill-name>/
        ├── SKILL.md          # 必须：元数据 + 指令
        └── references/       # 可选：参考资料
```
