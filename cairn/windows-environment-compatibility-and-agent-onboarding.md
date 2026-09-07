---
type: project_topic
status: active
summary: "Windows 环境下跨 Agent 同步踩坑实战：PowerShell 5.1 编码陷阱、NTFS Junction 免交互解绑、TOML 去重与 Skills Manager 全新部署纳管"
tags:
  - windows
  - powershell
  - ntfs-junction
  - toml
  - codex
  - skills-manager
  - encoding
contains:
  - decision
  - lesson
  - pattern
created: "2026-09-07"
updated: "2026-09-07"
related:
  - multi-device-sync-and-token-optimization.md
authoring_mode: ai_generated
---
# Windows 跨 Agent 技能同步与自动化配置避坑实战

## 形成背景 (Formation Context)
在第三台设备（当前便携工作机，用户名包含中文字符 `秋野恋理`）上首发部署 `agent-skills-workspace` 并纳管 Antigravity、OpenAI Codex 与 Skills Manager GUI 过程中，遭遇了无头环境挂起、文件编码乱码、TOML 解析器崩溃及全新 GUI 客户端数据库空白等一系列具有普遍代表性的工程难题。

## 当前结论 (Current Conclusions)
1. **Windows 原生 API 优先原则**：PowerShell 的高层 Cmdlet（如 `Remove-Item`、`Get-Content`）在无交互式 CLI、特殊编码及重解析点（Junction）场景下极不可靠，必须下沉到 .NET 原生静态方法（`[System.IO.Directory]::Delete`、`[System.IO.File]::ReadAllText`）以获得绝对的确定性。
2. **多语言配置文件的严格编码隔离**：跨平台 Agent（如基于 Rust 的 Codex 与基于 Go/C++ 的运行时）对 UTF-8 的 BOM 标记高度敏感；而 Windows PowerShell 5.1 解析带中文注释的脚本时又必须依赖 BOM。两者必须严格区分：**脚本带 BOM，配置文件一律强制无 BOM**。
3. **GUI 客户端与 CLI 状态解耦与补全**：单纯在文件系统建立 Junction 不足以让依赖本地 SQLite 数据库的 GUI 客户端（Skills Manager）识别“已受管理”。新机初始化脚本必须同时完成底层文件联接与 GUI 内部预设数据库注册。

## 决策记录 (Decision Log)
- **D-05 (Zero-Prompt Junction Teardown)**：废弃 `Remove-Item -Path $path -Force` 解绑 Junction 的做法，全面改用 .NET `[System.IO.Directory]::Delete($Path, $false)`。当目标为 Junction 时，系统仅毫秒级解绑重解析点目录项，**零交互提示、不递归、绝不伤及母本**。
- **D-06 (Strict Dual-Encoding Standard)**：
  - 本项目所有 `.ps1` 脚本文件：严格保存为 **UTF-8 with BOM**（防止 PowerShell 5.1 词法解析错位）；
  - 所有输出的配置（`config.toml`、`mcp_config.json`、`skills.json`）：强制采用 **UTF-8 without BOM**（防止 Rust/Go 解析器报 `invalid byte` 崩溃）。
- **D-07 (Idempotent TOML Section Replacement)**：重构 `sync-mcp.ps1` 中的正则匹配规则，使用跨行贪婪子表断言 `(?ms)\[mcp_servers\.github\](?:.(?!\r?\n\[(?!mcp_servers\.github)))*.`，确保无论执行多少次，旧服务及其所有 `.env` 子表都被整块覆盖，杜绝 Duplicate Table。
- **D-08 (Skills Manager Headless Seeding)**：在纯净新装机器上，通过 `skills-manager-cli skills install --local <temp-path> --sync` 自动对齐 Default Preset，并配合 `agents disable` 关停无对应软件的 Agent，使新机状态秒级对齐主力机。

## 避坑教训与关键模式 (Lessons & Patterns)

### 坑 1：PowerShell 5.1 `Remove-Item` 针对含子项 Junction 弹窗死锁
- **现象**：后台执行重定向或清理链接时，任务毫无报错但永久卡死。
- **根因**：`Remove-Item` 遇到有子项的目录联接点，若缺少 `-Recurse`，会在隐藏控制台弹出 `[Y] 是否要继续?`；而一旦加上 `-Recurse`，在旧版系统上又存在顺着链接误删母本内容的风险。
- **解法**：使用 `[System.IO.Directory]::Delete($path, $false)`，第二个参数 `$false` 确保仅解绑当前重解析点。

### 坑 2：`Get-Content` 导致中文路径乱码
- **现象**：Codex 配置文件中的用户路径 `C:\Users\秋野恋理` 变成了 `绉嬮噹鎭嬬悊`，导致环境路径失效。
- **根因**：PowerShell 5.1 的 `Get-Content -Raw` 默认以操作系统 ANSI 编码打开文件，遇到 UTF-8 文件中的中文时发生高字节截断损坏。
- **解法**：读写外部文件一律封装：
  ```powershell
  $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
  $content = [System.IO.File]::ReadAllText($filePath, $utf8NoBom)
  [System.IO.File]::WriteAllText($filePath, $newContent, $utf8NoBom)
  ```

### 坑 3：TOML 重复表头导致应用闪退
- **现象**：Codex 启动瞬间崩溃，日志或手动解析报 Duplicate Table。
- **根因**：TOML 不允许同名表头（如多个 `[mcp_servers.github.env]`）。旧脚本正则未将子表一并包含进替换区间。
- **解法**：在正则中精准划分块边界，严格保证每个服务及其子环境变量块唯一。
## 四、架构深化：业务专属技能与通用公共技能分离

在跨设备管理实践中，技能天然分为两类：
1. **通用公共技能 (Global SSOT)**：
   - 特点：跨项目通用（如 `systematic-debugging`、`project-cairn`、`teach` 等），存放于本中央库 `agent-skills-workspace/skills`。
   - 机制：通过 Git 仓库多端同步，并通过 `sync-skills.ps1` 以 NTFS Junction 挂载到所有全局 Agent 目录。
2. **业务专属技能 (Project-Bound Skills)**：
   - 特点：与特定项目源码强绑定（如酒店直连诊断 `hotel-pc-direct-diagnostics`、NAS 控制台 `qnap-nas-console`），离开对应工作区没有独立运行意义。
   - 机制：**随行工程化**。放置在业务项目根目录的 `.agents/skills/<skill-name>/`，随业务工程（如百度同步盘/项目 Git 仓库）版本化与跨端同步；同时在项目内创建 `.gemini/skills` 挂载点，并在全局 Agent 中软链接挂载，实现全局与项目局部访问零割裂。

## 五、联动机制：pull-sync.ps1 与 Skills Manager 双向打通

- 在 `scripts/pull-sync.ps1` 中加入第 4 步：检测并调用 `skills-manager-cli skills sync`。
- 无论开发者在终端使用命令行 `pull-sync.ps1`，还是后续打开 Skills Manager 桌面端 GUI，两者的预设、开关和可用技能状态始终保持 100% 实时一致。
