# Handoff: 跨设备与多 Coding Agent 技能/MCP 统一管理系统

本文档旨在为新会话提供完整的上下文交接，便于直接指定本目录作为工作区启动具体实施。

---

## 1. 背景与核心痛点 (Background & Pain Points)

用户日常在 **至少 3 台电脑** 上使用 **多个不同的 Coding Agent** 协同开发：
* **涉及的 Coding Agent**：`antigravity`、`antigravityIDE`、`grokbuild`、`codex` 以及 Cursor、Claude Code 等。
* **面临的核心痛点**：
  1. **重复安装与遗漏**：每台电脑、每个 Agent 都要重复配置 Skill 和 MCP，经常出现“以为电脑 B 的某个 Agent 装了某 Skill，实际上没装”的情况。
  2. **版本碎片化**：同一个 Skill 在部分电脑/Agent 上是新版，在另一些地方是旧版，难以维护。
  3. **生态与格式割裂**：
     * 格式差异：有些 Agent 只接受单文件 Markdown（如 `.cursor/rules/*.mdc`），有些需要文件夹 + `SKILL.md`（如 Antigravity / Gemini CLI），有些需要 `manifest.json` 或插件结构。
     * 路径差异：各 Agent 的配置目录和 MCP 文件散落在 `%APPDATA%`、`~/.gemini/`、`~/.cursor/`、`~/.claude/` 等各处。

---

## 2. 调研结论与选型分析 (Survey & Tech Stack)

经过前期技术调研，确认市面上已有针对性轮子，且各工具之间具备极佳的互补性：

1. **[skills-manage](https://github.com/iamzhihuix/skills-manage)（本地中央仓 + GUI 仪表盘）**
   * **作用**：基于 Tauri 的跨平台桌面端，自带中央技能库（如 `~/.agents/skills/`），支持 20+ 个 Agent 的一键部署（Deploy/Undeploy）和状态直观查看。
   * **定位**：作为本地各个 Agent 目录挂载和状态检查的 **GUI 控制中心**。

2. **[PRPM](https://github.com/pr-pm/prpm)（CLI 包管理器 + 多格式转译引擎）**
   * **作用**：类似 `npm` 的 AI 规则/技能包管理器，支持 `prpm install <pkg> --as <tool>`。
   * **优势**：能将标准技能包自动转译适配为单文件（Cursor MDC）、Claude Skills 或 Copilot 等不同规范。

3. **[sync-mcp](https://github.com/william-garden/sync-mcp) / [MCPM](https://github.com/pathwaycom/mcpm)**
   * **作用**：专用于抹平各 IDE/Agent 间 MCP Server 配置格式和路径差异的同步工具。

4. **Git + 符号链接 (Symlink / Junction)（跨 3 台电脑的同步底座）**
   * 作为“单一真实来源”（Single Source of Truth, SSOT），通过私有 Git 仓库将中央库推拉到各台电脑，再由本地工具映射至各 Agent。

---

## 3. 总体架构设计方案 (Proposed Architecture)

```text
               ┌──────────────────────────────────────────────┐
               │    GitHub / Gitee 私有仓库 (SSOT 技能中心库)    │
               │   - skills/ (标准 SKILL.md 文件夹形态)         │
               │   - mcp/ (通用 MCP Server 模板与环境变量映射)   │
               └──────────────────────┬───────────────────────┘
                                      │ git pull
       ┌──────────────────────────────┼──────────────────────────────┐
       ▼                              ▼                              ▼
    [电脑 A]                       [电脑 B]                       [电脑 C]
 终端 prpm / 导入              git pull 自动同步              git pull 自动同步
       │                              │                              │
       ▼                              ▼                              ▼
 D:\agent-skills-workspace\skills (作为 skills-manage 的中央本地库)
       │
       ├─► 格式 A (支持文件夹: Antigravity/Codex): 直接软链接 (mklink /J)
       ├─► 格式 B (单文件 MD: Cursor/Windsurf): PRPM 转译或简易脚本生成
       └─► GUI 呈现: 打开 skills-manage，直观查看所有 Agent 的开关与生效状态
```

---

## 4. 暂定目标与路线图 (Roadmap & Next Steps)

新会话启动后，请按照以下步骤逐步实施：

- [ ] **Step 1: 建立中央规范与目录结构**
  * 在当前工作区规范化建立 `skills/`、`mcp/`、`scripts/` 等目录。
  * 采用“最完备的文件夹母本规范”：每个技能为一个独立目录，内含带 YAML frontmatter 的 `SKILL.md`，可包含可选的 `scripts/` 与 `resources/`。
- [ ] **Step 2: 盘点当前环境的 Agent 路径与格式清单**
  * 梳理本机及跨机主要 Agent 的真实读取路径：
    * `antigravity` / `antigravityIDE`: `C:\Users\<user>\.gemini\antigravity\skills` 与 `C:\Users\<user>\.gemini\config\skills`
    * `codex` / `grokbuild` 的具体配置目录与期望格式
    * Cursor / Claude 等其他辅助 Agent 的路径
- [ ] **Step 3: 配置与联动测试**
  * 引入/配置 `skills-manage`，将其中央库路径定向到本工作区中的 `skills/`。
  * 测试从远端拉取/编写一个 Skill，验证其能否在 GUI 中正常显示并一键 Deploy 到目标 Agent。
- [ ] **Step 4: 编写 Windows 一键分发/跨端同步脚本**
  * 编写适配 Windows PowerShell 的轻量自动化脚本（处理 `mklink` 软链接创建、Git 同步拉取、以及非标准格式的简单转译）。
  * 配置敏感信息（API Key）与环境变量隔离方案（`.env` 模板，避免秘钥同步泄露）。

---

## 5. 建议调用的技能 (Suggested Skills)

新会话 Agent 接手时，建议激活/查阅以下技能协助开发：
* **`writing-great-skills`**：用于规范化编写和校验符合标准生态的高质量 Skill 结构。
* **`antigravity-guide`** / **`agy-customizations`**：查阅 Antigravity 生态下 Skill 和 MCP 的加载规则与优先级。
* **`systematic-debugging`**：排查软链接权限、路径不存在或多 Agent 配置加载失败时的排查支持。
