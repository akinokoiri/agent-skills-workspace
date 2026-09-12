# Project Cairn Log

This file records substantive progress in reverse-chronological order — newest entry at the top, right below this line. Keep each entry short — summary and pointer only; conclusions settle into `cairn/<topic>.md`.

## 2026-09-12 · 按自用项目整理公开介绍

- 用户决定公开既有仓库；README 明确自用定位、AI 协助维护和第三方内容来源，不作全仓原创或统一许可声明。
- 公开前检查当前跟踪文件及可达历史中的凭据模式，保留已有许可；说明见 [README](../README.md#内容来源与许可)。

## 2026-09-12 · 在仓库介绍明确 Agent 更新流程

- README 为 Codex 的本仓库 skills 更新请求定义完整本机流程：技能正文与入口核验、委派策略应用及完整提示验收；用户限定的范围优先。
- AGENTS 增加按请求触发的入口指针；Git 拉取脚本仍不隐式修改配置。详见 [README 更新流程](../README.md#给执行更新的-agent)。

## 2026-09-12 · Codex 委派策略独立分发

- 将低频 Luna 监控与主代理异常处理策略纳入 Git，以独立脚本仅合入本机指定配置键；普通技能拉取不隐式部署。
- 增加完整提示核验、Windows 写入锁、ACL 备份与失败回滚；缩短策略，拒绝提示中间截断后的伪成功。
- 部署步骤、兼容边界与验证方式见 [Codex 委派策略同步](codex-policy-sync.md)。

## 2026-09-12 · 按任务加载规则与不确定回答处理

- grilling 增加具体场景与间接线索验证，允许无偏好、暂缓和已授权的默认选择；小批提问、按收益委派，并以当前决策范围限定结束条件。
- Cairn 模板按任务读取状态，完成检查排除只读与进度播报；维护参考和实例升级说明同步调整，spec 日期为 2026-09-12。
- 仓库局部编辑与强制覆盖按可恢复条件区分备份要求；本轮仍按修改前规则保存原文件和恢复清单。
- 决策与验证边界见 [提示词与不确定回答处理](prompt-refinement-2026-09-12.md)。

## 2026-09-08 · 多机 Git 更新与本机部署分离

- 用户确认通用技能源；修复拉取、导入、格式校验及挂载的失败边界，默认更新正文不隐式调用 Skills Manager。
- setup 收窄为技能入口配置；保留本机物理冲突与定制规则，旧的“预演仍写入”和失败后继续行为纳入隔离验证。
- 核对 SM 的过期临时来源及当前正确联接，来源迁移须在推送后备份并使用受支持接口；不复制设备数据库。
- 真实来源预检发现 SM 会把冗余 true 工具记录重建为缺省值，已从部署和 GUI 两个入口核对有效选择；表示变化与实际配置变化分别记录。
- 远端 Windows CI 暴露测试夹具的短路径别名比较问题；统一解析临时根路径，保留原保护断言。
- 规则与验收边界见 [技能多机同步契约](skill-sync-contract.md)。

## 2026-09-08 · 按当前差异修复规则与技能正文

- 修复规则冲突、缺失参考、任务范围和历史指针；原文件按 SHA-256 比对后备份，保留其他 Agent 已完成的修正。
- Skills Manager、多机 Git 来源及同步/安装脚本按用户要求延后；不将本轮内容修复视为同步链路验收。
- 记录基线测试意外调用真实 Skills Manager CLI 的影响证据与验证边界。
- 详情见 [规则与技能增量修复](rule-skill-repair-2026-09-08.md)。

## 2026-09-07 · pull-sync.ps1 联动 Skills Manager 与业务专属技能随行化

- 完成 `scripts/pull-sync.ps1` 自动化升级：拉取技能并挂载后，自动调用 `skills-manager-cli skills sync`，打通 CLI 与 GUI 状态同步。
- 架构优化落地：将酒店直连诊断（`hotel-pc-direct-diagnostics`）与 NAS 控制台（`qnap-nas-console`）完成项目随行工程化改造，源文件迁入对应工程的 `.agents/skills/`，通过百度同步盘实现双机自动同步，全局 Agent 目录通过 Junction 软链穿透，彻底解耦通用公共库与业务专用库。
- 详情与完整知识沉淀：参见 [cairn/windows-environment-compatibility-and-agent-onboarding.md](windows-environment-compatibility-and-agent-onboarding.md)。

## 2026-09-07 · 便携工作机部署实战、Junction 免交互安全解绑与 Codex 编码修复

- 完成便携工作机（用户名 `秋野恋理`）跨 Agent SSOT 中央库首次接入与全环境就绪。
- 根因排查与攻克 PowerShell 5.1 下 Junction 删除引发的隐藏交互弹窗，引入 .NET 原生 `Directory::Delete` 实现零交互解绑。
- 修复 `sync-mcp.ps1` 在 PowerShell 5.1 下默认 ANSI 导致中文路径乱码、以及正则跨行断言引发 Codex `config.toml` 重复表闪退问题。
- 部署并打通 `skills-manager` GUI（v1.36.2）与 CLI，批量完成 10 大核心公共技能的 Default Preset 纳管与未安装 Agent 过滤，与主力机视图对齐。
- 详情与完整知识沉淀：参见 [cairn/windows-environment-compatibility-and-agent-onboarding.md](windows-environment-compatibility-and-agent-onboarding.md)。

## 2026-09-06 · 跨机技能同步架构优化与零 Token 规范落地

- 完成了多机（主机与 Surface Pro 11）技能同步与跨 Agent 分发架构优化。
- 确立了零 Token 极速收纳工具（`scripts/import-skill.ps1`）与一键拉取自愈工具（`scripts/pull-sync.ps1`）。
- 在 Surface Pro 11 上实机验证了双向收纳、安全时间戳备份、推送与 NTFS Junction 挂载自愈闭环。
- 修复了 GitHub Actions CI 脚本转义报错，实测工作流转为全部绿色通过。
- 踩坑沉淀：WinCredMan 无头死锁解决、Base64 SSH 传参、PS 5.1 BOM 规范与 CI 单独脚本化。
- 详情与完整知识总结：参见 [cairn/multi-device-sync-and-token-optimization.md](multi-device-sync-and-token-optimization.md)。

## 2026-09-06 · Project Cairn 初始化

- 初始化 Project Cairn 规范档案结构（`.cairn/config.yaml`）。
- 设定 Git 策略为 `track`（共享多端项目记忆），语言为 `zh`。
- 详情参见 `.cairn/config.yaml`。
