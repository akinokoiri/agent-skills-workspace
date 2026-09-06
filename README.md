# Agent Skills & MCP 统一管理中心 (SSOT)

> **面向多设备（主机、Surface、笔记本、远程服务器）与多 Coding Agent 的中央技能仓库与极速分发中枢。**  
> 核心哲学：**“确定性脚本在系统层干重活，绝不让 LLM 当数据搬运工” —— 极致节省 Token，100% 杜绝格式损坏与合并冲突。**

---

## 1. 架构总览与核心设计

```text
                           ┌─────────────────────────────────────────┐
                           │    GitHub 远程中央库 (Single Source of Truth) │
                           │       akinokoiri/agent-skills-workspace  │
                           │  - skills/ (标准 SKILL.md 母本库)        │
                           │  - .github/workflows/ (云端防错 CI 守门)  │
                           └────────────────────┬────────────────────┘
                                                │
                 ┌──────────────────────────────┴──────────────────────────────┐
       git pull / push (毫秒级系统流转)                               git pull / push
                 │                                                             │
      ┌──────────▼──────────┐                                       ┌──────────▼──────────┐
      │   【主力电脑 / 主机】  │                                       │   【便携本 / Surface】│
      │ G:\agent-skills-workspace                                   │ C:\...\agent-skills-workspace
      │ (NTFS Junction 零拷贝)                                       │ (NTFS Junction 零拷贝)
      └──────────┬──────────┘                                       └──────────┬──────────┘
                 │                                                             │
  ┌──────────────┴──────────────────────────────┐               ┌──────────────┴──────────────────────────────┐
  ├─► ChatGPT / Codex:       ~/.codex/skills/   │               ├─► ChatGPT / Codex:       ~/.codex/skills/   │
  ├─► Grok / grokbuild:      ~/.grok/skills/    │               ├─► Grok / grokbuild:      ~/.grok/skills/    │
  ├─► DeepSeek Harness:      ~/.dsh/skills/     │               ├─► DeepSeek Harness:      ~/.dsh/skills/     │
  ├─► Antigravity / Gemini:  ~/.gemini/skills/  │               ├─► Antigravity / Gemini:  ~/.gemini/skills/  │
  ├─► Claude Code:           ~/.claude/skills/  │               ├─► Claude Code:           ~/.claude/skills/  │
  └─► GUI: skills-manager 桌面端仪表盘实时纳管   │               └─► GUI: skills-manager 桌面端仪表盘实时纳管   │
  └─────────────────────────────────────────────┘               └─────────────────────────────────────────────┘
```

### 为什么这样设计？
1. **单一真实源 (Single Source of Truth, SSOT)**：技能母本全部统一存放在 GitHub 仓库的 `skills/` 目录中。
2. **NTFS Junction 本地零拷贝**：各个 Agent 目录并非复制副本，而是 Windows 原生**目录联接点 (Junction)**。只要中央库更新，所有 Agent 实时生效，**无需重启、无需重复同步、普通权限免提权**。
3. **零 Token 损耗与防错原则 (Zero-Token Payload)**：绝对严禁让 AI Agent 把成百上千行的 Skill 代码/文档读入对话上下文来搬运。所有技能入库、校验、推送均由本地脚本毫秒级完成，Agent 仅需调用一条命令（消耗 < 100 Tokens）。
4. **云端全自动守门 (GitHub Actions CI)**：内置 `validate-skills.yml` 自动化工作流。任何机器或网页端提交如果缺少 `SKILL.md` 或 YAML Frontmatter 格式不合规，CI 会立即阻断并报警，确保中央库 100% 纯净。

---

## 2. 人类开发者使用指南 (Human Guide)

### 场景 1：在其他机器（如 Surface、出差电脑）发现了好用的 Skill，如何上传？
> **核心解答**：**绝不需要回到主机再装！** 你在任何机器都可以随时上传同步。

#### 途径 A：其他机器上也 Clone 了本仓库（最推荐）
1. 在其他机器运行导入脚本，自动完成**格式校验、冲突检测、备份、本地挂载与 Git 远端推送**：
   ```powershell
   # 从本地某个 Agent 目录或临时目录导入，并一键推送到 GitHub
   .\scripts\import-skill.ps1 -SourcePath "C:\path\to\new-skill" -Push

   # 或直接从某个外部开源 Git 仓库拉取收纳并推送
   .\scripts\import-skill.ps1 -GitUrl "https://github.com/someone/cool-skill.git" -Push
   ```
2. **回到主机后**：只需敲一句一键同步命令：
   ```powershell
   .\scripts\pull-sync.ps1
   ```
   脚本会自动保护本地未提交内容、拉取最新代码，并自动为新技能在主机的各个 Agent 目录补齐 NTFS Junction 软链接。

#### 途径 B：其他机器没有工作区，但装有 Agent（如 Claude Code / Antigravity）
无需手动操作 Git，直接对那台机器上的 Agent 说一句：
> *“帮我把这个 skill 复制到我的 GitHub 仓库 `akinokoiri/agent-skills-workspace` 的 `skills/<skill-name>` 目录下并 push，不要在上下文中打印全文。”*

#### 途径 C：临时电脑 / 手机端 / 浏览器中直接发现
直接打开 GitHub 网页版仓库，在 `skills/` 下点击 **Add file -> Upload files** 上传该技能目录。云端 CI 会自动进行合规性验证。

---

### 场景 2：新电脑/老设备首次初始化与就绪
只需在新机上克隆仓库并执行初始化脚本：
```powershell
git clone https://github.com/akinokoiri/agent-skills-workspace.git
cd agent-skills-workspace
powershell -ExecutionPolicy Bypass -File .\scripts\setup-device.ps1
```
* 全自动检测 Git、Node.js 等环境；
* 自动安全备份旧版本的物理冲突目录；
* 自动为所有已安装的 Agent 建立 Junction 软链接；
* 自动同步 Antigravity 索引与 GitHub MCP 接入。

---

### 场景 3：日常编辑与维护
* **修改现有技能**：直接在 `skills/<skill-name>/SKILL.md` 中编辑保存即可，本机的所有 Agent 即刻感知新指令。
* **推送修改**：`git commit -am "feat: update prompt" && git push`。
* **拉取更新**：`.\scripts\pull-sync.ps1`。

---

## 3. AI Agent 操作手册 (Agent Operating Guide)

如果你是负责协助用户操作本仓库的 AI Agent（Antigravity、Claude Code、Codex、Grok 等），请**严格遵守 [AGENTS.md](file:///g:/agent-skills-workspace/AGENTS.md) 中的三大铁律**：

1. **绝对禁止数据搬运**：严禁调用读取文件工具把整个技能目录的内容吐在对话上下文里。执行收纳必须使用确定性脚本。
2. **严格守门**：所有新技能必须包含标准的 YAML Frontmatter（包含非空的 `name:` 与 `description:`）。
3. **命令速查映射**：

| 用户意图 | Agent 应调用的终端命令 |
| :--- | :--- |
| **“帮我把这个新 skill 加进库里”** | `powershell -File .\scripts\import-skill.ps1 -SourcePath "<path>" -Push` |
| **“更新已有技能并覆盖”** | `powershell -File .\scripts\import-skill.ps1 -SourcePath "<path>" -Force -Push` |
| **“从远程 Git 导入技能”** | `powershell -File .\scripts\import-skill.ps1 -GitUrl "<url>" -Push` |
| **“拉取最新技能 / 同步更新”** | `powershell -File .\scripts\pull-sync.ps1` |
| **“查看当前各 Agent 技能挂载状态”** | `powershell -File .\scripts\sync-skills.ps1 -Status` |
| **“修复损坏链接与挂载”** | `powershell -File .\scripts\sync-skills.ps1 -Force` |

---

## 4. 自动化脚本清单与功能速查

| 脚本路径 | 核心功能 | 典型使用场景 |
| :--- | :--- | :--- |
| **`scripts/import-skill.ps1`** | **零 Token 技能导入与上传**<br>含 SKILL.md 格式校验、YAML 审查、防重名冲突备份、自动 Rebase Push。 | 在任何机器收纳新发现的技能并一键发布到 GitHub。 |
| **`scripts/pull-sync.ps1`** | **一键拉取与自动自愈**<br>内置本地脏工作区 Stash 保护、远端更新拉取，并自动为新技能建立 Junction 挂载。 | 从机提交后，主机一键对齐最新状态。 |
| **`scripts/sync-skills.ps1`** | **跨 Agent NTFS Junction 挂载引擎**<br>自动清理坏死链接，免提权秒级打通 5+ 大主流 Agent。 | 查看技能挂载状态、清理历史死链接。 |
| **`scripts/setup-device.ps1`** | **新机全自动就绪工具**<br>涵盖依赖检测、历史版本安全备份、Agent 挂载、MCP 注入与 GUI 联动。 | 任何新电脑或刚重装系统的电脑首发配置。 |
| **`scripts/sync-mcp.ps1`** | **跨 Agent MCP 服务配置注入**<br>提取 GitHub PAT 并注入 Antigravity 及 Codex 配置文件。 | 更新 MCP Token 或管理 MCP Server。 |

---

## 5. 常见问题 (FAQ)

#### Q1: 为什么使用 NTFS Junction，而不是直接用 Git 软链接 (Symlink)？
Windows 上创建符号链接（Symlink）默认需要管理员提权或开启开发者模式；而 **NTFS Junction（目录联接点）是 Windows 原生文件系统特性，普通用户权限即可秒级建立**，且对 Node.js、Python、Go、Rust 跨平台运行时 100% 透明兼容。

#### Q2: 如果在其他机器提交了同名技能，会覆盖主机的改动吗？
不会。`import-skill.ps1` 内置了版本冲突检测，若目标已存在同名技能，不加 `-Force` 会直接安全报警拒绝执行；加了 `-Force` 也会先在 `backups/<timestamp>/` 创建物理快照备份。

#### Q3: 为什么说这个架构“极致节省 Token”？
传统的 Agent 协作方式是让模型读取整篇几千行的文档并重新生成，一次流转消耗数万 Tokens，且模型可能会发生代码转义损毁。本仓库全部通过操作系统级命令与 Git 底层管道流转，**LLM 只充当决策调度者，不充当数据搬运工**，单次操作 Token 消耗从上万降至不足 100。
