# Handoff: 跨设备与多 Coding Agent 技能/MCP 统一管理系统

本文档记录当前统一管理系统的最新实施状态、决策共识、核心资产清单与后续演进路线，便于未来会话或跨设备协同随时无缝接续。

---

## 1. 核心定位与设计共识 (Core Concept & Consensus)

针对用户日常在 **3+ 台电脑** 上使用 **多个 Coding Agent**（`Antigravity` / `Antigravity IDE`、`ChatGPT / Codex`、`Grok / grokbuild`、`DeepSeek Harness`、`Claude Code` 等）面临的“配置碎片化、技能版本漂移、坏死链接”痛点，本系统确立了以下治理铁律：

1. **单一真实源 (Single Source of Truth, SSOT)**：
   * 远端以私有 Git 仓库 [`akinokoiri/agent-skills-workspace`](https://github.com/akinokoiri/agent-skills-workspace) 为母本。
   * 本地以 `G:\agent-skills-workspace\skills\` 为唯一权威目录。
2. **免提权 NTFS Junction 本地零拷贝分发**：
   * 本地各 Agent 统一通过 Windows 目录联接（Junction）挂载中央母本，编辑一处、处处实时生效，绝不复制副本。
3. **严格的分层准入与边界隔离**：
   * **全局通用方法 (纳入中央库)**：严谨排错流程、跨会话交接、设计树对齐、技能编写标准、工程沉淀框架。
   * **工具专有技能 (保留在本地生态)**：Antigravity 的 25+ GCP/BigQuery/Airflow 技能留在本地；Grok 的工程自检与 DeepSeek Harness 的角色扮演技能留在各自专属生态，不混入中央库。
   * **业务专属技能 (项目随行管理)**：绑定企业特定环境（如 `gpo_read`、`windows-update-activity`、`mac_data`、`floor_plans`）的技能留在各自工程的 `.agents/skills/` 目录中，随工程 Git 仓库走，严防污染全局 Prompt 上下文。

---

## 2. 实施进度与现状里程碑 (Completed Milestones)

- [x] **Step 1: 建立中央规范与目录结构**
  * 规范建立了 `skills/`、`mcp/`、`scripts/` 等目录。
  * 采用“独立文件夹 + 带 YAML frontmatter 的 `SKILL.md`”最高兼容度通用形态。
- [x] **Step 2: 资产全面盘点与冲突治理**
  * 梳理了 Antigravity、Codex、Grok、DSH 及百度同步盘（`G:\BaiduSyncdisk`）的全部技能与 MCP。
  * 发现了版本严重分化的 4 个高频技能（`grill-me`, `grilling`, `handoff`, `writing-great-skills`），并确立了统一标准。
  * 发现并修复了 `~/.codex/skills/` 中 6 个指向失效百度盘路径的坏死软链接。
- [x] **Step 3: 开源工具链安装与 GUI 纳管**
  * 安装 `skills-manager` (v1.36.2)、`prpm` (v2.1.39)、`sync-mcp` (v0.1.5)。
  * `skills-manager` 桌面端与 CLI 已完整索引中央库全部 10 项技能。
- [x] **Step 4: 编写 Windows 一键挂载自动化脚本**
  * 编写 [`scripts/sync-skills.ps1`](file:///g:/agent-skills-workspace/scripts/sync-skills.ps1)，支持坏死链接自动清理、冲突物理文件夹安全备份、NTFS Junction 挂载与状态健康度审计（`-Status`）。
  * 已成功挂载到本机活跃的 5 个 Agent，实现 100% 联通。
- [x] **Step 5: GitHub 远程私有中心库推送**
  * 依托 GitHub MCP 创建私有仓库，全部技能母本、脚本与文档已推送到 `origin main`。

---

## 3. 当前中央资产全景 (Inventory)

### 3.1 核心通用技能库 (10 项)

| 技能名称 | 来源/规范 | 核心职责 |
| :--- | :--- | :--- |
| **`grilling`** | Matt Pocock 官方最新版 | 深度对齐面试，基于**设计树**与 **Frontier 决策前沿**逐轮推进，直到无任何默认假设。 |
| **`grill-me`** | Matt Pocock 官方最新版 | 快捷触发别名，直接跳转调用 `grilling`。 |
| **`grill-with-docs`**| Matt Pocock 官方最新版 | 深度工程对齐版，自动在会话中产出并维护 `CONTEXT.md` 与 ADR 架构决策记录。 |
| **`handoff`** | Matt Pocock 官方最新版 | 紧凑交接文档生成，支持参数提示、凭证脱敏与下一步推荐技能。 |
| **`writing-for-agents`**| Matt Pocock 官方最新版 | 技能编写核心规范（梯子模型、渐进披露、抗过早完成、Leading Words）。 |
| **`writing-great-skills`**| 官方兼容别名 | 别名跳转至 `writing-for-agents`，兼容历史提示词。 |
| **`teach`** | Matt Pocock 官方最新版 | 体系化互动教学，附带学习记录、词汇表与教案全套模板。 |
| **`project-cairn`** | 百度盘精选沉淀 | 工程资产知识结晶框架，防项目经验漂移与文档陈旧。 |
| **`task-checkpoint`** | 百度盘精选沉淀 | 跨会话/换设备/下班前的任务断点快照保存与复工恢复。 |
| **`systematic-debugging`**| Antigravity 精选提拔 | 严谨的排错纪律，强制假设验证与根因取证，防盲目盲改。 |

### 3.2 各 Agent 本地当前挂载映射表

| Agent 目标目录 | 挂载方式 | 状态 |
| :--- | :--- | :--- |
| **Antigravity / Gemini CLI** (`~/.gemini/config/skills`) | NTFS Junction | ✓ 10 项正常联接（独占 25+ GCP 技能保留） |
| **ChatGPT (Codex)** (`~/.codex/skills`) | NTFS Junction | ✓ 10 项正常联接（坏死旧链接已清理） |
| **Grok (grokbuild)** (`~/.grok/skills`) | NTFS Junction | ✓ 10 项正常联接（独占 check-work 等保留） |
| **DeepSeek Harness** (`~/.dsh/skills`) | NTFS Junction | ✓ 10 项正常联接（独占 RP 技能保留） |
| **Claude Code** (`~/.claude/skills`) | NTFS Junction | ✓ 10 项正常联接 |

---

## 4. 跨设备同步操作规范 (Multi-Machine Workflow)

当在**电脑 B** 或**电脑 C** 上同步与维护本套体系时，执行标准操作流：

1. **首次部署**：
   ```powershell
   git clone https://github.com/akinokoiri/agent-skills-workspace.git G:\agent-skills-workspace
   npm install -g prpm sync-mcp
   cd G:\agent-skills-workspace
   .\scripts\sync-skills.ps1
   ```
2. **日常同步更新**：
   * 在电脑 A 修改或新增技能后：`git add . && git commit -m "feat: add skill" && git push`
   * 在电脑 B / C 终端只需执行：`git pull`
   * **无需重新挂载**：因为本地 Agent 都是通过 Junction 动态读取 `G:\agent-skills-workspace\skills\`，Git 文件的更新会瞬间对所有 Agent 生效。
3. **状态检查**：
   ```powershell
   .\scripts\sync-skills.ps1 -Status
   ```

---

## 5. 下一步建议与后续路线 (Roadmap & Next Steps)

未来接手本工作区的 Agent 可依据用户需求推进以下演进：

1. **MCP 跨端自动化同步联动**：
   * 进一步利用 `sync-mcp` 或扩充 `scripts/`，在检测到新 MCP 时支持一键推送到 Codex (`config.toml`)、Grok (`config.toml`) 或 Claude Desktop 配置中。
2. **Cursor / MDC 格式转译自动化**：
   * 若后续在部分电脑上增加 Cursor / Windsurf，可利用已安装的 `prpm` 将中央库标准文件夹转译为 `.cursor/rules/*.mdc` 单文件。
3. **CI / 质量校验管线**：
   * 在 GitHub 私有仓库中添加 GitHub Action 或 pre-commit 钩子，自动基于 `writing-for-agents` 的规范校验新增技能的 YAML frontmatter 完整性。
