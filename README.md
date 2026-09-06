# Agent Skills & MCP 统一管理中央库 (SSOT)

本仓库作为跨设备（3+ 台电脑）及跨 Coding Agent（Antigravity、Antigravity IDE、Grok Build、Codex、Cursor、Claude Code 等）的技能 (Skills) 与 MCP Server 配置的单一真实来源 (Single Source of Truth, SSOT)。

---

## 1. 架构与工具链

* **[skills-manager](https://github.com/xingkongliang/skills-manager)**: 本地 GUI 仪表盘与 CLI，管理中央技能库与 20+ 个 Coding Agent 的部署状态。
* **[prpm](https://github.com/pr-pm/prpm)**: CLI 包管理器与跨格式转译引擎（转译为 Cursor MDC、Claude Skills 等）。
* **[sync-mcp](https://github.com/william-garden/sync-mcp)**: MCP 配置一键跨 Agent 同步工具。
* **Git + 符号链接 (Symlink/Junction)**: 跨机器云端同步与本地各 Agent 配置目录挂载。

---

## 2. 目录规范

```text
agent-skills-workspace/
├── skills/             # 标准 Skill 母本目录（支持文件夹 + SKILL.md 规范）
├── mcp/                # 通用 MCP Server 配置模板与映射
│   ├── mcp-servers.json # 通用 MCP 声明
│   └── .env.example    # 敏感环境变量与 API 密钥模板（不提交真实 Key）
├── scripts/            # 自动化跨端同步与软链接挂载脚本 (PowerShell)
├── HANDOFF.md          # 需求背景、调研记录与 Roadmap
└── README.md           # 本文档
```

---

## 3. 快速上手

1. **克隆仓库**:
   ```bash
   git clone https://github.com/akinokoiri/agent-skills-workspace.git
   ```
2. **安装核心工具**:
   * `skills-manager`: 已提供 CLI (`skills-manager-cli.exe`) 与 Desktop GUI。
   * `prpm`: `npm install -g prpm`
   * `sync-mcp`: `npm install -g sync-mcp`
