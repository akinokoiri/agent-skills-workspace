# Agent Skills & MCP 统一管理中心 (SSOT)

本仓库作为跨设备（3+ 台电脑）及多 Coding Agent（Antigravity、Antigravity IDE、Grok Build、ChatGPT/Codex、DeepSeek Harness、Claude Code 等）的技能 (Skills) 与 MCP Server 配置的单一真实来源 (Single Source of Truth, SSOT)。

---

## 1. 架构与工具链体系

```text
               ┌──────────────────────────────────────────────────────────┐
               │    GitHub 远程私有仓库 (SSOT 技能中心库)                     │
               │    akinokoiri/agent-skills-workspace                     │
               │    - skills/ (标准 SKILL.md 文件夹母本库)                  │
               │    - mcp/ (通用 MCP 模板与密钥隔离规范)                    │
               └────────────────────────────┬─────────────────────────────┘
                                            │ git pull / push
        ┌───────────────────────────────────┼───────────────────────────────────┐
        ▼                                   ▼                                   ▼
   [电脑 A: 主机]                      [电脑 B: 笔记本]                    [电脑 C: 办公机]
  G:\agent-skills-workspace           G:\agent-skills-workspace           G:\agent-skills-workspace
        │                                   │                                   │
        │ scripts\sync-skills.ps1           │ scripts\sync-skills.ps1           │ scripts\sync-skills.ps1
        ▼                                   ▼                                   ▼
  ┌─────────────────────────────────────────────────────────────────────────────┐
  │ 本地免提权 NTFS Junction (目录联接点)                                        │
  ├─► ChatGPT / Codex:       ~/.codex/skills/                                   │
  ├─► Grok / grokbuild:      ~/.grok/skills/                                    │
  ├─► DeepSeek Harness:      ~/.dsh/skills/                                     │
  ├─► Antigravity / Gemini:  ~/.gemini/config/skills/                           │
  ├─► Claude Code:           ~/.claude/skills/                                  │
  └─► GUI 控制台:            skills-manager 桌面端仪表盘实时纳管与启闭           │
  └─────────────────────────────────────────────────────────────────────────────┘
```

* **[skills-manager](https://github.com/xingkongliang/skills-manager)** (v1.36.2): 本地 GUI 桌面仪表盘与 CLI，管理中央技能库与 20+ 个 Coding Agent 的部署状态。
* **[prpm](https://github.com/pr-pm/prpm)** (v2.1.39): CLI 包管理器与跨格式转译引擎（转译为 Cursor MDC、Claude Skills 等）。
* **[sync-mcp](https://github.com/william-garden/sync-mcp)** (v0.1.5): MCP 配置一键跨 Agent 同步工具。
* **Git + NTFS Junction**: 跨机器云端同步底座，本地免提权目录联接，彻底杜绝多版本碎片化。

---

## 2. 目录规范与文件清单

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
├── HANDOFF.md                  # 跨会话完整技术交接与实施档案
└── README.md                   # 本说明文档
```

---

## 3. 技能分层与准入规范 (Governance Rules)

经充分审视与决策树对齐，本工作区严格遵守**三层治理原则**：

1. **中央收录 (Global / Universal Skills)**：
   * 仅收录高复用度的核心研发方法论、严谨排错流程、跨会话交接及深度对齐沟通工具（上述 10 大技能）。
   * 必须符合标准文件夹形态：包含带 YAML frontmatter 的 `SKILL.md`，可包含可选的 `references/`、`assets/` 或脚本。
2. **专有保留 (Agent-Specific Skills)**：
   * **Antigravity**：独占的 25+ 个 GCP/BigQuery/Airflow 大数据技能保留在 `~/.gemini/config/skills/` 本地，不混入中央库。
   * **Grok (grokbuild)**：专有的 `check-work`、`code-review`、`imagine` 等留在 Grok 本地。
   * **DeepSeek Harness**：专有的角色扮演（RP）与模型插件留在 DSH 本地。
3. **项目跟随 (Project-Bound Skills)**：
   * 强绑定企业或业务环境的特定技能（如 `gpo_read`、`windows-update-activity`、`mac_data`、`floor_plans` 等）严格保存在对应项目代码库的 `.agents/skills/` 目录中，随具体业务 Git 仓库走，**严禁混入全局中央库，防污染全局 Prompt 上下文**。

---

## 4. 快速上手与多机部署 (Quick Start)

### 4.1 在新电脑 (电脑 B / 电脑 C) 上配置

在新机器上只需执行以下两步：

```powershell
# 1. 克隆私有仓库
git clone https://github.com/akinokoiri/agent-skills-workspace.git G:\agent-skills-workspace

# 2. 全局安装辅助 CLI (需 Node.js 18+)
npm install -g prpm sync-mcp

# 3. 运行一键挂载与健康检查
cd G:\agent-skills-workspace
.\scripts\sync-skills.ps1
```

脚本执行时将自动完成：
* 扫描并彻底清理目标 Agent 目录中指向已失效路径的坏死链接；
* 若目标存在旧版冲突的物理副本，安全归档至 `backups/<timestamp>/`；
* 为本机已检测到的所有 Agent（Codex、Grok、DSH、Antigravity、Claude Code）免提权创建指向中央库的 NTFS Junction。

### 4.2 检查挂载状态
随时在终端运行：
```powershell
.\scripts\sync-skills.ps1 -Status
```
即可实时列出各 Agent 的联接有效性与健康度。

### 4.3 使用桌面 GUI 仪表盘
已安装的 **`skills-manager`** 可直接在 Windows 开始菜单启动：
* 可视化查看每个技能在各个 Agent 上的部署/激活状态；
* 一键开启或关闭单个 Agent 对某个技能的感知；
* 技能有更新时直接在此处刷新或搜索生态新技能。

---

## 5. 日常维护与协同工作流

* **修改现有技能**：在 `skills/<skill-name>/SKILL.md` 中编辑。由于各 Agent 均是 Junction 直连，**修改后本地所有 Agent 瞬间生效**，无需重启或重新挂载。
* **添加新通用技能**：
  1. 在 `skills/` 下新建技能目录与 `SKILL.md`；
  2. 运行 `.\scripts\sync-skills.ps1` 将新技能挂载至所有 Agent；
  3. 执行 `skills-manager skills adopt G:\agent-skills-workspace\skills` 让 GUI 刷新索引。
* **多电脑同步推送**：
  * **在修改机器**：
    ```bash
    git add .
    git commit -m "feat: add or update skill"
    git push origin main
    ```
  * **在其他电脑**：
    ```bash
    git pull origin main
    ```
    拉取完成后，底层文件更新会即刻同步穿透至所有 Agent，无需重复运行挂载脚本。

---

## 6. 常见问题 (FAQ & Troubleshooting)

* **Q: 为什么使用 NTFS Junction 而不是普通软链接 (Symlink)？**
  * **A**: 在 Windows 上，创建符号链接（`mklink /D` 或 `New-Item -ItemType SymbolicLink`）默认需要管理员权限或启用开发者模式；而 **NTFS Junction（目录联接点）是 Windows 原生文件系统特性，普通用户权限即可秒级创建**，且绝大多数跨平台运行时（Node.js, Python, Rust, Go）均将其透明视为普通目录，兼容性最佳。
* **Q: 为什么 Codex 里不能留旧的软链接？**
  * **A**: 当软链接指向的源目录（例如百度网盘中的历史项目）被重命名或移除后，会成为“悬空坏死链接”（Dangling Junction），导致 Agent 扫描 skills 目录时抛出底层 IO 异常。脚本已内置坏链自动侦测与清理机制。
* **Q: 敏感 API Key 如何处理？**
  * **A**: 中央库通过 `.gitignore` 严格忽略了 `.env`、`*.local` 与 `backups/`。MCP 相关密钥仅在 `mcp/.env.example` 维护占位模板，真实密钥通过本机系统环境变量或本地 `.env` 隔离，确保私有 Git 仓库纯净安全。
