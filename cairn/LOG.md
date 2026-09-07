# Project Cairn Log

This file records substantive progress in reverse-chronological order — newest entry at the top, right below this line. Keep each entry short — summary and pointer only; conclusions settle into `cairn/<topic>.md`.

## 2026-09-07 · 便携工作机部署实战、Junction 免交互安全解绑与 Codex 编码修复

- 完成便携工作机（用户名 `秋野恋理`）跨 Agent SSOT 中央库首次接入与全环境就绪。
- 根因排查与攻克 PowerShell 5.1 下 Junction 删除引发的隐藏交互弹窗，引入 .NET 原生 `Directory::Delete` 实现零交互解绑。
- 修复 `sync-mcp.ps1` 在 PowerShell 5.1 下默认 ANSI 导致中文路径乱码、以及正则跨行断言引发 Codex `config.toml` 重复表闪退问题。
- 部署并打通 `skills-manager` GUI（v1.36.2）与 CLI，批量完成 10 大核心公共技能的 Default Preset 纳管与未安装 Agent 过滤，与主力机视图对齐。
- 详情与完整知识沉淀：参见 [cairn/windows-environment-compatibility-and-agent-onboarding.md](file:///D:/agent-skills-workspace/cairn/windows-environment-compatibility-and-agent-onboarding.md)。

## 2026-09-06 · 跨机技能同步架构优化与零 Token 规范落地

- 完成了多机（主机与 Surface Pro 11）技能同步与跨 Agent 分发架构优化。
- 确立了零 Token 极速收纳工具（`scripts/import-skill.ps1`）与一键拉取自愈工具（`scripts/pull-sync.ps1`）。
- 在 Surface Pro 11 上实机验证了双向收纳、安全时间戳备份、推送与 NTFS Junction 挂载自愈闭环。
- 修复了 GitHub Actions CI 脚本转义报错，实测工作流转为全部绿色通过。
- 踩坑沉淀：WinCredMan 无头死锁解决、Base64 SSH 传参、PS 5.1 BOM 规范与 CI 单独脚本化。
- 详情与完整知识总结：参见 [cairn/multi-device-sync-and-token-optimization.md](file:///g:/agent-skills-workspace/cairn/multi-device-sync-and-token-optimization.md)。

## 2026-09-06 · Project Cairn 初始化

- 初始化 Project Cairn 规范档案结构（`.cairn/config.yaml`）。
- 设定 Git 策略为 `track`（共享多端项目记忆），语言为 `zh`。
- 详情参见 `.cairn/config.yaml`。
