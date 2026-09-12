# Agent Operating Guidelines & Workspace Protocols

This repository (`akinokoiri/agent-skills-workspace`) serves as the **Single Source of Truth (SSOT)** for AI Coding Agent skills and MCP configurations across multiple devices and agents (Antigravity, Claude Code, ChatGPT Codex, Grok, DeepSeek Harness, etc.).

These protocols govern work in this repository. Resolve the repository root before running the relative commands below; they do not make this file a global rule for other projects.

---

## 1. 核心铁律：零 Token 损耗与防错原则 (Zero-Token & Anti-Error)

### 🔴 铁律一：禁止 LLM 上下文数据搬运 (Zero-Token Payload Principle)
* **严禁**：调用读取工具将整个 Skill 目录、成百上千行的 `SKILL.md` 或脚本全文读入对话上下文，再通过模型输出写入目标路径。
  - *后果*：单次无谓消耗 10,000 ~ 50,000 Tokens，且极易引发换行符损毁、转义字符丢失或上下文截断。
* **强制要求**：所有技能的收纳、迁移、同步必须下沉给操作系统层确定性脚本执行。Agent 调用脚本并检查退出状态、目标文件和挂载结果。审计、调试与内容修改时可读取相关正文；原样搬运使用文件复制，避免让模型重打包。

### 🔴 铁律二：必须经过格式合规校验 (Validation Before Ingestion)
任何新技能入库前，必须保证：
1. 包含核心定义文件 `SKILL.md`；
2. 头部包含标准 YAML Frontmatter（`---` 包裹），且必须含有非空的 `name:` 与 `description:`；
3. 技能目录名必须与 `name` 保持完全一致（全部小写，仅包含字母、数字与连字符，如 `my-new-skill`）。

### 🔴 铁律三：防冲撞与备份隔离 (Conflict Prevention)
* 严禁无预警覆盖已有同名技能；
* 对已纳入 Git 且工作区基线干净的文件做局部编辑时，使用 Git 差异与提交保留可审查历史，无需额外复制备份。强制导入、覆盖冲突副本，或变更前状态无法从 Git 恢复时，先在 `backups/<timestamp>/` 保存原文件与恢复清单。
* 只修改已确认归属本任务的内容，不覆盖用户或其他协作者的未提交改动；备份不构成覆盖授权。

---

## 2. Agent 任务行动指令手册 (Action Playbook)

按用户已授权的动作选择对应脚本。安装或导入默认仅本地；只有明确要求提交/上传远端时添加 `-Push`。检查状态与执行同步分开，不把脚本退出成功等同于业务验收。导入和拉取默认只更新中央内容；只有明确选择脚本管理入口的设备按需加 `-Sync`。

### 场景 A：用户要求收纳或安装；上传是独立的可选动作
- **输入形式 1：本地目录或从其他 Agent 发现**
  ```powershell
  # 仅导入到本地工作区
  .\scripts\import-skill.ps1 -SourcePath "C:\path\to\new-skill"

  # 明确要求提交/上传该项导入，且仓库干净时
  .\scripts\import-skill.ps1 -SourcePath "C:\path\to\new-skill" -Push

  # 若已存在同名技能需更新并备份
  .\scripts\import-skill.ps1 -SourcePath "C:\path\to\new-skill" -Force
  ```
- **输入形式 2：从外部 Git 仓库拉取单个技能**
  ```powershell
  .\scripts\import-skill.ps1 -GitUrl "https://github.com/user/cool-skill.git"
  ```

### 场景 B：拉取远端更新；默认只更新 Git 文件
```powershell
.\scripts\pull-sync.ps1

# 只读本地状态，不拉取、不部署
.\scripts\pull-sync.ps1 -Status

# 仅适用于已选择脚本管理入口的设备，显式拉取后补建入口
.\scripts\pull-sync.ps1 -Sync
```

普通拉取要求干净的 main 和 origin/main 跟踪关系，采用 ff-only；失败保留现场，不自动 stash/pop/rebase。Skills Manager 管理的设备不附加 -Sync，已有联接随中央文件更新。

### 场景 C：检查或修复脚本管理的入口
```powershell
.\scripts\sync-skills.ps1 -Status
.\scripts\sync-skills.ps1 -DryRun

# 审查差异后应用；默认保留冲突并报告未完成
.\scripts\sync-skills.ps1
```

只有明确决定备份并替换普通冲突副本时才使用 -Force；未知链接仍保留。Skills Manager 和脚本不轮流控制同一目标的开关。

### 场景 D：新设备使用脚本配置技能入口
```powershell
.\scripts\setup-device.ps1
```

---

## 3. 全局行为与变更纪律 (Agent Operating Guidelines)

1. **策略调整与继续执行**：
   - 原计划内紧凑推进；策略显著变化时先简要说明事实和下一步，再继续已授权的工作。
   - 只有必要输入或权限缺失、后续动作超出授权时暂停依赖该条件的步骤；保留其他独立工作的进展。
2. **严谨求实**：
   - 未经验证的动作严禁声称成功；严格区分【已确认事实】与【推测/待核实】。
3. **最小侵入原则**：
   - 避免格式化或重写无关代码；优先采用精准局部修改。
