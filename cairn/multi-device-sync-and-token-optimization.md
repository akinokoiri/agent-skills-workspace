---
type: project_topic
status: active
summary: "跨设备技能同步架构设计、零 Token 损耗规范、自动化守门 CI 与无头 SSH 排障总结"
tags:
  - multi-device
  - skills-sync
  - token-optimization
  - powershell
  - ssh
  - github-actions
contains:
  - decision
  - lesson
  - pattern
created: "2026-09-06"
updated: "2026-09-06"
related: []
authoring_mode: ai_generated
---
# 跨设备技能同步、零 Token 损耗与无头运维工程实践

## 形成背景 (Formation Context)
本项目作为跨电脑（主力台式机、便携 Surface Pro 11 等）与跨 Agent（Antigravity、Claude Code、Codex、Grok、DSH）的技能单一真实源（SSOT）。针对“其他机器发现新技能是否必须回主机发起同步”的核心疑问，确立了以 GitHub 远程仓库为中心枢纽、多端对等提交、本地 NTFS Junction 零拷贝穿透的架构，并完成了基于 Surface Pro 11 实机的双向验证。

## 当前结论 (Current Conclusions)
1. **GitHub 仓库是中央唯一真相源**：主机与从机本质是对等的分支节点。任何设备（哪怕没有完整工作区，只要具备 Git / GitHub API 通道）均可向仓库推送技能，主机仅需拉取并增量自愈挂载。
2. **确定性脚本下沉原则**：所有格式审查、时间戳备份、目录搬运下沉给 PowerShell/Python 脚本，严禁 LLM 在对话上下文做长篇文本流转。
3. **云端 CI 与本地自愈结合**：通过 GitHub Actions 守门保证入库技能 100% 具备合法 `SKILL.md`，通过 `sync-skills.ps1` 在本地毫秒级自愈挂载与清理死链。

## 决策记录 (Decision Log)
- **D-01 (Zero-Token Ingestion)**：建立 `scripts/import-skill.ps1`，入库技能由操作系统毫秒级拷贝并正则校验 YAML 元数据，单次操作 Token 消耗从上万降至 `< 100`。
- **D-02 (Pull & Auto-Mount)**：建立 `scripts/pull-sync.ps1`，集成 `git stash` 保护、`git pull --rebase` 与 `sync-skills.ps1`，实现多机协同的一键拉取挂载闭环。
- **D-03 (Decoupled CI Validation)**：将 CI 检查逻辑从 YAML 内联 Bash 提取至独立脚本 `scripts/validate-skills.py`，彻底杜绝 Shell 引号转义引发的假报错。
- **D-04 (Headless Tokenized Git URL)**：在无头远程设备（如 Surface SSH）配置带 PAT 的 remote origin，避开无法调起 GUI 弹窗的 WinCredMan 死锁。

## 关键模式 (Experience & Patterns)
- **模式 1：NTFS Junction 零拷贝穿透**
  Windows 目录下使用 NTFS Junction（免提权、普通用户可建），将中央库目录穿透至各 Agent 路径（`~/.gemini/config/skills`、`~/.codex/skills` 等），底层文件修改实时全量生效。
- **模式 2：Base64 穿透远程执行**
  跨 SSH 执行含引号、分号、管道符的复杂 PowerShell 逻辑时，统一用 `[Convert]::ToBase64String(...)` 编码，配合 `powershell -EncodedCommand` 规避任何命令行转义解析歧义。
- **模式 3：BOM 编码分治策略**
  跨机 PowerShell 脚本（`.ps1`）显式采用 **UTF-8 with BOM**（保证 PowerShell 5.1 解析含 Emoji/中文时不丢引号）；数据文件（`.json` / `.md` / `.yml`）保持 **UTF-8 without BOM**（保证各跨平台解析器兼容）。

## 踩坑教训 (Lessons)
- **L-01 (WinCredMan SSH Hang)**：Windows 凭据管理器在无交互终端下无法弹出认证窗口，导致 Git 报 `could not read Username`。解法：配置带 Token 的 URL 覆盖默认 credential helper。
- **L-02 (Inline CI Quoting Bug)**：在 GitHub Actions YAML 中写 `python -c '...'` 内嵌正则单引号导致 Bash 解析截断报 `syntax error near unexpected token '('`。教训：复杂 CI 逻辑严禁内联，必须独立为 `.py` 文件。
- **L-03 (PowerShell 语法冒号冲突)**：PowerShell 字符串中 `"$dirName: msg"` 会被误认为是作用域变量。教训：变量紧贴冒号时强制包裹表达式 `"$($dirName): msg"`。
- **L-04 (Dangling Junctions)**：远端删除技能后本地 Junction 变为空指向，会引起部分 Agent 扫描异常。教训：挂载脚本必须内置 `Test-BrokenLink` 并在同步前执行静默清理。
