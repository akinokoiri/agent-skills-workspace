# Agent Skills & MCP 统一管理中央库 (SSOT)

本仓库作为跨设备（3+ 台电脑）及跨 Coding Agent（Antigravity、Antigravity IDE、Grok Build、ChatGPT/Codex、DeepSeek Harness、Claude Code 等）的技能 (Skills) 与 MCP Server 配置的单一真实来源 (Single Source of Truth, SSOT)。

---

## 1. 架构与工具链

* **[skills-manager](https://github.com/xingkongliang/skills-manager)**: 本地 GUI 仪表盘与 CLI，管理中央技能库与 20+ 个 Coding Agent 的部署状态。
* **[prpm](https://github.com/pr-pm/prpm)**: CLI 包管理器与跨格式转译引擎（转译为 Cursor MDC、Claude Skills 等）。
* **[sync-mcp](https://github.com/william-garden/sync-mcp)**: MCP 配置一键跨 Agent 同步工具。
* **Git + NTFS Junction**: 跨机器云端同步底座，本地免提权目录联接，彻底杜绝多版本碎片化。

---

## 2. 目录结构

```text
agent-skills-workspace/
├── skills/                     # 标准 Skill 母本目录（独立文件夹 + SKILL.md）
│   ├── grilling/               # [Matt 官方最新] 深度设计树对齐与 Frontier 轮次面试
│   ├── grill-me/               # [Matt 官方最新] 快捷触发 grilling 别名
│   ├── grill-with-docs/        # [Matt 官方最新] 架构与 ADR 文档对齐版
│   ├── handoff/                # [Matt 官方最新] 跨 Agent/跨会话无损上下文交接
│   ├── writing-for-agents/     # [Matt 官方最新] 梯子模型与高预见性技能编写规范
│   ├── writing-great-skills/   # [兼容别名] 转发至 writing-for-agents
│   ├── teach/                  # [Matt 官方最新] 体系化技能教学与教案模板
│   ├── project-cairn/          # [通用工程资产] 项目知识沉淀与防漂移架构
│   ├── task-checkpoint/       # [通用工程资产] 任务断点快照与开工恢复
│   └── systematic-debugging/   # [严谨排错流程] 假设驱动与根因取证系统排查
├── mcp/                        # 通用 MCP Server 配置模板与映射
│   ├── mcp-servers.json        # 通用 MCP 声明
│   └── .env.example            # 敏感环境变量与 API 密钥模板（不提交真实 Key）
├── scripts/
│   └── sync-skills.ps1         # 跨 Agent 自动化 NTFS Junction 挂载与坏死链接清理脚本
├── HANDOFF.md                  # 需求背景、调研记录与 Roadmap
└── README.md                   # 本文档
```

---

## 3. 技能边界与准入规范

经对齐，本中心库严格遵守**分层治理规范**：

1. **中央收录 (Global Skills)**：仅收录高复用度的研发方法论、严谨排错流程、跨会话交接及对齐沟通工具（上述 9 大核心技能）。
2. **专有保留 (Agent-Specific)**：
   * Antigravity 的 25+ 个 GCP/BigQuery/Airflow 大数据技能保留在本地，不混入中央库。
   * Grok (`check-work`, `code-review` 等)、DeepSeek Harness 角色扮演等专属技能保留在各自生态中。
3. **项目跟随 (Project-Bound)**：
   * 强绑定企业或业务环境的技能（如 `gpo_read`, `windows-update-activity`, `mac_data`, `floor_plans` 等）严格保存在对应工程的 `.agents/skills/` 目录中，随业务 Git 仓库走，不污染全局上下文。

---

## 4. 跨设备与新机器快速上手指南

在电脑 B 或电脑 C 上配置时，仅需 2 步：

### Step 1: 克隆本仓库并安装基础工具
```powershell
# 1. 克隆仓库
git clone https://github.com/akinokoiri/agent-skills-workspace.git G:\agent-skills-workspace

# 2. 全局安装 CLI 工具 (需 Node.js 18+)
npm install -g prpm sync-mcp
```

### Step 2: 一键挂载所有 Agent 技能
```powershell
cd G:\agent-skills-workspace
.\scripts\sync-skills.ps1
```
脚本将自动：
* 扫描并清理各 Agent 目录下的坏死软链接与残留文件；
* 备份原有的物理冲突副本至 `backups/`；
* 为 `Codex`、`Grok`、`DeepSeek Harness`、`Antigravity`、`Claude Code` 免提权创建指向中央库的 NTFS Junction；
* 运行 `.\scripts\sync-skills.ps1 -Status` 可随时查看所有 Agent 的挂载健康状态。

---

## 5. 日常维护与更新

* **添加新技能**：在 `skills/<skill-name>/` 下创建标准 `SKILL.md`，运行 `.\scripts\sync-skills.ps1` 即可瞬间同步生效至所有本地 Agent。
* **多电脑同步**：
  * 在修改端：`git add . && git commit -m "feat: add skill" && git push`
  * 在其他电脑：`git pull` 即可（Junction 会自动感知底层文件变化，无需重新挂载）。
