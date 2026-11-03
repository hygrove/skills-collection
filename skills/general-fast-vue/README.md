# general-fast-vue —— FastAPI + Vue3 单端口全栈项目架构技能

> 搭建「一个后端进程、一个端口，同时提供业务接口 + SPA 页面 + 静态资源 + 数据」这类项目时用的**操作规约**。
> 不是通用教程，是**已踩过的坑**——每条约束都配一个能跑的机器闸门。

---

## 一句话说明

这类项目的骨架（FastAPI + Vue3 + SQLite）三天就能搭完，但**坑在骨架之后**：
挂载顺序错了图片全 404、比率存进表里汇总口径就错、跑批把用户改的数据冲掉、
写死端口导致本地能跑云端起不来……

这个技能把那些坑固化成 **8 条铁律 + 5 个闸门脚本**。

---

## 目录结构

```
general-fast-vue/
├── SKILL.md                              # 主体：8 条铁律 + 8 步流程（AI 读这个）
├── references/                           # 按需查阅（AI 不会一次性全读）
│   ├── handbook-full.md                  #   完整架构手册（36 条约束 + 迁移速查）
│   ├── read-write-layering.md            #   读写分层：三层模型 + 修正层设计 + 两个缺口
│   ├── deployment-and-portability.md     #   迁移性 + 云端部署：五种形态 + 六条铁律 + 失败模式
│   ├── adr-and-context-formats.md        #   ADR 与 CONTEXT.md 写法模板
│   └── adr-019-stack-verdict.md          #   【样本】一份真实的 ADR，写法示范
└── scripts/                              # 五个闸门（可执行，退出码即结果）
    ├── check_mount_order.py              #   静态挂载顺序
    ├── check_ratio_columns.py            #   比率列不入库
    ├── check_append_only.py              #   事实表只增不减
    ├── check_no_bare_print.py            #   用 logging 不用裸 print
    └── check_portability.py              #   无绝对路径 / 无硬编码端口
```

---

## 五个闸门怎么用

```bash
# 在项目根目录下执行（路径按你的项目实际位置替换）
python <skill>/scripts/check_mount_order.py    <项目>/backend/app --mode spa
python <skill>/scripts/check_ratio_columns.py  <项目>/backend
python <skill>/scripts/check_append_only.py    <项目>/backend
python <skill>/scripts/check_no_bare_print.py  <项目>/backend
python <skill>/scripts/check_portability.py    <项目> --allow-port 5173
```

**退出码即结果**：`0` = 通过，`1` = 违规。可直接接 CI 或推送前钩子。

| 闸门 | 拦什么 | 不拦会怎样 |
|---|---|---|
| `check_mount_order.py` | 静态挂载写在业务路由之后 | 页面能开，图片全 404（浏览器拿到 200+HTML，不报错） |
| `check_ratio_columns.py` | 事实表里存了比率列 | 单日数据对、汇总数据错（10%、20% → 真实 15%，平均只是巧合） |
| `check_append_only.py` | 事实表被逐行 DELETE/UPDATE | 跑批冲掉用户修改 / 源表移走后行冻结成僵尸行 |
| `check_no_bare_print.py` | 应用代码用裸 print | 无控制台启动时 print 静默蒸发，诊断信息一行落不了盘 |
| `check_portability.py` | 绝对路径字面量 / 固定端口 | 本地能跑、云端起不来（健康检查失败、流量进不来） |

### 常用参数

| 参数 | 适用闸门 | 用途 |
|---|---|---|
| `--mode spa\|api\|auto` | `check_mount_order.py` | 同源托管 SPA / 纯后端 API / 自动判定（默认） |
| `--fact-table 表名` | `check_append_only.py` | 显式声明事实表（优先于特征词识别） |
| `--exempt-table 表名` | `check_append_only.py` | 豁免可写表（像事实表但允许逐行删改） |
| `--allow-port 端口` | `check_portability.py` | 声明该端口允许写死（如 dev 的 5173） |

### 豁免范围（脚本内已内置）

`verify_*` / `check_*` / `setup_*` / `test_*` 与 `tests/` / `scripts/` 下的 CLI 工具与测试——
它们的 `print` 是给人看的输出、它们的删改是造夹具数据，都不是业务行为。

---

## 什么时候用、什么时候不用

**适合**：
- 数据从 Excel/CSV/接口批处理进来，要看板、要指标库、要分析
- 要单端口同时托管接口 + SPA + 图片
- 需要人工修正数据或维护主数据（读写分层）
- 要部署到云端 / 发成在线链接 / 换个机器还能跑

**不太适合**：
- **纯 CRUD 后台**（用户输入为主、无批处理数据源）→ 跳过步骤 2 与 2.5，直接从步骤 3 开始
- 换技术栈（不是 FastAPI + Vue3）→ 闸门脚本要重写，但**规则可以移植**

---

## 换栈时的移植方式

闸门脚本是 Python + FastAPI + SQLite 专属的，但**背后的判据是语言无关的**。
换栈时优先移植规则：

| 规则 | 换栈后的对应机制 |
|---|---|
| 静态挂载顺序 | Express 的 `app.use` / Go 的 `http.Handle` / Django 的 urlpatterns 顺序 |
| 比率不入库 | 不变（与存储无关） |
| 只增不减 | 不变（与存储无关） |
| 无裸输出 | 换成本语言对应的输出函数 |
| 无硬编码路径/端口 | 不变 |

---

## 维护约定

- **SKILL.md 是常驻部分**（AI 启动时读它），保持精简；
- **`references/` 是按需加载**——某条约束需要完整「为什么 + 避坑」时才去读；
- **改闸门脚本后必须用正反例双向验证**：能「跑通」不等于「能抓住」；
- **误报比漏报更危险**——误报一多就被人加豁免绕过，闸门随即失效。判定要刻意收窄。

---

## 来源

从真实项目（电商数据可视化，单端口 FastAPI + Vue3 + SQLite）的架构实践中萃取，
经三轮交叉实测（让独立 AI 实例专门挑错）迭代而成——共修复 30+ 个缺陷，
包括 5 处「闸门给假通过」的严重问题。
