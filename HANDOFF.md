# Handoff: 跨设备与多 Coding Agent 技能/MCP 统一管理系统

本文件保留 2026-09-06 至 2026-09-07 的部署交接快照；其中版本、数量和完成项不是持续更新的当前状态。当前规则与命令见 [AGENTS.md](AGENTS.md)、[README.md](README.md)，后续变更见 [cairn/LOG.md](cairn/LOG.md)。 当前多机操作见 [README.md](README.md) 与 [同步契约](cairn/skill-sync-contract.md)；下文旧一键自动联动流程已被取代。2026-09-08 审计修复记录见 [规则与技能修复](cairn/rule-skill-repair-2026-09-08.md)。

---

## 1. 核心定位与设计共识 (Core Concept & Consensus)

针对用户日常在 **3+ 台电脑** 上使用 **多个 Coding Agent**（`Antigravity` / `Antigravity IDE`、`ChatGPT / Codex`、`Grok / grokbuild`、`DeepSeek Harness`、`Claude Code` 等）面临的“配置碎片化、技能版本漂移、坏死链接”痛点，本系统确立了以下治理铁律：

1. **单一真实源 (Single Source of Truth, SSOT)**：
   * 远端以私有 Git 仓库 [`akinokoiri/agent-skills-workspace`](https://github.com/akinokoiri/agent-skills-workspace) 为母本。
   * 每台设备以实际仓库根下的 `skills/` 为通用技能源；本次核对设备的仓库根为 `D:\agent-skills-workspace`，其他设备不得照搬盘符。
2. **免提权 NTFS Junction 本地零拷贝分发**：
   * 本地各 Agent 统一通过 Windows 目录联接（Junction）挂载中央母本，源文件由联接共享；客户端是否重载仍需验证，历史物理副本不代表当前来源。
3. **定向分发与环境隔离 (Selective Target Dispatch)**：
   * **通用技能**：全量广播挂载至所有 Agent（如排错纪律、面试对齐、交接存档）。
   * **专属/增强技能**：通过分发过滤器白名单精准定向推送。例如 `progress-brief` 仅供给 Antigravity 与 Grok；对于原生已内置阶段反馈机制的 Codex 和 DeepSeek Harness，分发脚本自动排除并不予挂载，彻底杜绝提示词冗余与行为冲突。
   * **业务专属技能**：源文件留在工程 `.agents/skills/`；若需全局可发现，入口必须识别项目根与目标环境。源文件归属和发现范围是两个独立配置。

---

## 2. 实施进度与现状里程碑 (Completed Milestones)

- [x] **Step 1: 建立中央规范与目录结构**
  * 规范建立 `skills/`、`mcp/`、`scripts/` 等目录，采用标准 `SKILL.md` 规范。
- [x] **Step 2: 资产全面盘点与冲突治理**
  * 统一了高频分化技能，治理并清理了历史坏死软链接。
- [x] **Step 3: 开源工具链安装与 GUI 纳管**
  * `skills-manager` (v1.36.2) 桌面端与 CLI 已完整纳管中央库。
- [x] **Step 4: 编写 Windows 一键挂载自动化脚本**
  * 编写 [`scripts/sync-skills.ps1`](scripts/sync-skills.ps1)，支持自动查杀坏死链接、冲突物理文件夹备份与健康度审计（`-Status`）。
- [x] **Step 5: GitHub 远程私有中心库推送**
  * 依托 GitHub 建立私有仓库，实现跨电脑 Git 同步底座。
- [x] **Step 6: 新增 `progress-brief` 过程透明技能与定向分发架构升级**
  * **技能纳管**：引入 `progress-brief`，定义多步骤任务阶段性简报（8 个关键触发时机）、事实与推测严格边界、修改前报备与验证闭环。
  * **分发机制升级**：在 `sync-skills.ps1` 中新增 `$SkillTargetFilters` 白名单过滤表。仅向 `Antigravity`、`Antigravity (Skills Manager)` 和 `Grok (grokbuild)` 挂载 `progress-brief`；对 `Codex`、`DeepSeek Harness`、`Claude Code` 自动排除并在检测到残留时自动清理。
  * **全局规则联动**：
    * Antigravity 全局生效：`~/.gemini/config/rules/AGENTS.md`；独立偏好文件为 `~/.gemini/config/GEMINI.md`
    * Grok (grokbuild) 全局生效：`~/.grok/rules/AGENTS.md`

---

## 3. 历史部署资产快照（数量以记录当时为准）

### 3.1 核心通用技能库 (11 项)

| 技能名称 | 适用 Agent 范围 | 核心职责 |
| :--- | :--- | :--- |
| **`progress-brief`** | **Antigravity / Grok 定向** | 阶段性过程透明简报，事实/判断/推测严格隔离，禁止虚假声称完成与盲目重试。 |
| **`grilling`** | 全量所有 Agent | 深度对齐面试，基于设计树与 Frontier 决策前沿逐轮推进，挖出隐藏假设。 |
| **`grill-me`** | 全量所有 Agent | 快捷触发别名，直接跳转调用 `grilling`。 |
| **`grill-with-docs`**| 全量所有 Agent | 深度工程对齐版，自动在会话中产出并维护 `CONTEXT.md` 与 ADR 架构决策记录。 |
| **`handoff`** | 全量所有 Agent | 紧凑交接文档生成，支持参数提示、凭证脱敏与下一步推荐技能。 |
| **`writing-for-agents`**| 全量所有 Agent | 技能编写核心规范（梯子模型、渐进披露、抗过早完成、Leading Words）。 |
| **`writing-great-skills`**| 全量所有 Agent | 官方兼容别名，跳转至 `writing-for-agents`。 |
| **`teach`** | 全量所有 Agent | 体系化互动教学，附带学习记录、词汇表与教案全套模板。 |
| **`project-cairn`** | 全量所有 Agent | 工程资产知识结晶框架，防项目经验漂移与文档陈旧。 |
| **`task-checkpoint`** | 全量所有 Agent | 跨会话/换设备/下班前的任务断点快照保存与复工恢复。 |
| **`systematic-debugging`**| 全量所有 Agent | 严谨排错纪律，强制假设验证与根因取证，杜绝盲目改动。 |

### 3.2 当时的 Agent 挂载映射表

| Agent 目标目录 | 挂载方式 | 挂载技能数 | 定向过滤策略与状态 |
| :--- | :--- | :--- | :--- |
| **Antigravity (原生引擎)** (`~/.gemini/config/skills`) | NTFS Junction | **11 项** | ✓ 全量 + `progress-brief`（独占 GCP 技能保留） |
| **Antigravity (GUI 视图)** (`~/.gemini/antigravity/skills`)| NTFS Junction | **11 项** | ✓ 全量 + `progress-brief`（供 Skills Manager 索引） |
| **Grok (grokbuild)** (`~/.grok/skills`) | NTFS Junction | **11 项** | ✓ 全量 + `progress-brief`（专属规则在 `~/.grok/rules/`） |
| **ChatGPT (Codex)** (`~/.codex/skills`) | NTFS Junction | **10 项** | ✓ 通用 10 项（`progress-brief` 已被规则排除，原生自带） |
| **DeepSeek Harness** (`~/.dsh/skills`) | NTFS Junction | **10 项** | ✓ 通用 10 项（`progress-brief` 已被规则排除，原生自带） |
| **Claude Code** (`~/.claude/skills`) | NTFS Junction | **10 项** | ✓ 通用 10 项（`progress-brief` 已被规则排除） |

---

## 4. 跨设备同步操作规范 (Multi-Machine Workflow)

当在**电脑 B (Surface Pro 11)** 或**电脑 C (办公机)** 上同步时：

1. **日常拉取更新**：
   ```powershell
   # 先进入本机实际的仓库克隆目录，勿复制其他设备盘符
   git pull
   .\scripts\sync-skills.ps1
   ```
   * 脚本会自动识别各 Agent，并根据 `$SkillTargetFilters` 自动完成白名单定向挂载与排除项清理。
2. **状态健康度检查**：
   ```powershell
   .\scripts\sync-skills.ps1 -Status
   ```

---

## 5. 当时的后续建议（执行前重新核对当前规则与授权）

未来接手本工作区的 Agent 可推进：

1. **已完成：全局行为准则与意外转向阻断法则**：
   - 已在中央库 `rules/AGENTS.md` 建立基准，当时包含转向硬停止条款；2026-09-08 已改为先说明再继续已授权工作，以当前规则源为准。
   - `scripts/sync-skills.ps1` 已内置自动分发逻辑，在执行同步时自动将中央规则拷贝至 Antigravity (`~/.gemini/config/rules`) 与 Grok (`~/.grok/rules`)，实现跨机器规则一致性。
2. **MCP 跨端同步联动**：继续依托 `sync-mcp` 将中央模板自动化映射给各 Agent 的 MCP 配置。
3. **远端私有库 Git 凭据自动化**：针对 Surface Pro 在无界面 SSH 会话中无法调用 `wincredman` 的问题，可评估在 Surface 上配置专属只读 Personal Access Token (PAT) 或专用部署 SSH Key。