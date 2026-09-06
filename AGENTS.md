# Agent Operating Guidelines & Workspace Protocols

This repository (`akinokoiri/agent-skills-workspace`) serves as the **Single Source of Truth (SSOT)** for AI Coding Agent skills and MCP configurations across multiple devices and agents (Antigravity, Claude Code, ChatGPT Codex, Grok, DeepSeek Harness, etc.).

When any AI Agent operates within this workspace or is asked to manage skills, the following protocols MUST be followed.

---

## 1. 核心铁律：零 Token 损耗与防错原则 (Zero-Token & Anti-Error)

### 🔴 铁律一：禁止 LLM 上下文数据搬运 (Zero-Token Payload Principle)
* **严禁**：调用读取工具将整个 Skill 目录、成百上千行的 `SKILL.md` 或脚本全文读入对话上下文，再通过模型输出写入目标路径。
  - *后果*：单次无谓消耗 10,000 ~ 50,000 Tokens，且极易引发换行符损毁、转义字符丢失或上下文截断。
* **强制要求**：所有技能的收纳、迁移、同步必须下沉给操作系统层确定性脚本执行。Agent 仅需发出单行执行命令并观察退出代码（Exit Code）。

### 🔴 铁律二：必须经过格式合规校验 (Validation Before Ingestion)
任何新技能入库前，必须保证：
1. 包含核心定义文件 `SKILL.md`；
2. 头部包含标准 YAML Frontmatter（`---` 包裹），且必须含有非空的 `name:` 与 `description:`；
3. 技能目录名必须与 `name` 保持完全一致（全部小写，仅包含字母、数字与连字符，如 `my-new-skill`）。

### 🔴 铁律三：防冲撞与备份隔离 (Conflict Prevention)
* 严禁无预警覆盖已有同名技能；
* 当更新已有技能时，必须自动在 `backups/<timestamp>/` 创建物理备份，确保具备毫秒级回滚能力。

---

## 2. Agent 任务行动指令手册 (Action Playbook)

当人类用户向 Agent 提出以下需求时，Agent 应直接调用对应的确定性脚本执行：

### 场景 A：用户要求“收纳 / 安装 / 上传新技能”
- **输入形式 1：本地目录或从其他 Agent 发现**
  ```powershell
  # 仅导入到本地工作区
  .\scripts\import-skill.ps1 -SourcePath "C:\path\to\new-skill"

  # 导入并一键推送至 GitHub 触发全局同步
  .\scripts\import-skill.ps1 -SourcePath "C:\path\to\new-skill" -Push

  # 若已存在同名技能需更新并备份
  .\scripts\import-skill.ps1 -SourcePath "C:\path\to\new-skill" -Force -Push
  ```
- **输入形式 2：从外部 Git 仓库拉取单个技能**
  ```powershell
  .\scripts\import-skill.ps1 -GitUrl "https://github.com/user/cool-skill.git" -Push
  ```

### 场景 B：用户要求“拉取远端更新 / 同步最新技能”
```powershell
# 一键安全拉取 (含 stash 保护) 并自动为新技能补全 NTFS Junction 挂载
.\scripts\pull-sync.ps1

# 同步后顺便查看各 Agent 挂载健康状态
.\scripts\pull-sync.ps1 -Status
```

### 场景 C：用户要求“检查技能健康度 / 清理坏死链接”
```powershell
# 查看状态
.\scripts\sync-skills.ps1 -Status

# 强制修复、清理历史死链接并刷新挂载
.\scripts\sync-skills.ps1 -Force
```

### 场景 D：用户在新电脑上要求“一键配置环境”
```powershell
.\scripts\setup-device.ps1
```

---

## 3. 全局行为与变更纪律 (Agent Operating Guidelines)

1. **意外转向阻断法则 (Pivot Interruption Rule)**：
   - 连续执行查询、构建、测试无异常时，保持紧凑吞吐；
   - 当命令或工具遇到非预期报错，且准备放弃原方案改用备选方案时：**本轮禁止直接发出新工具调用**，必须先向用户说明：已确认错误、为何转向、拟采用的替代方案。
2. **严谨求实**：
   - 未经验证的动作严禁声称成功；严格区分【已确认事实】与【推测/待核实】。
3. **最小侵入原则**：
   - 避免格式化或重写无关代码；优先采用精准局部修改。
