---
type: project_topic
authoring_mode: ai_generated
contains: [decision, lesson, procedure]
summary: Codex 以交付结果和变化选择工作量，保留独立验收；五条专用规则通过 Git 分发、各设备显式部署。
---

# Codex 工程执行规则

## 背景与结论

本规则来自两个 Windows Update 实施任务的复盘：第一轮在已有方案的基础上反复准备、核对和拆分交付，主线迟迟未完成；接续轮复用已完成工作、精简重复验证后完成 Lab 测试并推进到单机灰度。两个任务起点和执行方式不同，不能据此计算删掉某项检查的独立收益或故障概率。

可复用经验是：按当前交付选择最短完整路径；新增准备或检查须有增量价值；验证围绕结果与变化；协作以完整交付为单位；修复时机按对当前任务的影响安排。需要修的问题可以在阶段边界集中处理，发现问题不自动意味着立即中断主线。

用户要求仅调整 Codex。Gemini 过早宣布完成的使用经验，是保留独立验收的原因；不能以精简为由直接接受完成声明，也不将个体使用经验写成普遍模型能力结论。原拟“发现交付停滞后纠偏”的第六条被删去：触发太晚且增加常驻注意力负担。此次保留五条，不另造定期自查流程或专用 skill。

正式条文仅维护在 [rules/codex/AGENTS.md](../rules/codex/AGENTS.md)。Gemini／Grok 的 `rules/AGENTS.md`、共享协作约定和 Codex 委派策略均为不同对象，本次未修改其内容。

## 部署

Git 更新共享源；各设备显式运行 [sync-codex-rules.ps1](../scripts/sync-codex-rules.ps1)：

```powershell
# 预览，不创建目录或修改本机规则。
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync-codex-rules.ps1 -DryRun

# 部署，仅写本机 Codex AGENTS.md。
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync-codex-rules.ps1
```

Windows PowerShell 5.1 可运行。目标由 `-CodexHome`、`CODEX_HOME`、用户目录下的 `.codex` 依次选择；显式路径须为绝对路径。源文件缺失或为空时失败。

- 目标缺失或为空：原样复制仓库文件。
- 内容一致：返回 `ALREADY_CURRENT`，不重写。
- 内容不同：返回退出码 2，保留本机文件；先比较并合并本机定制。脚本不提供强制覆盖开关。
- 目标为链接或目录：保留并报错，由设备维护者核对管理方式。

设备中已经合并的额外定制可能使下次仍报告差异；这表示需要审查合并，不代表上次部署失败。普通 Git 拉取不自动部署，脚本不改 `config.toml`、Gemini／Grok、技能入口或其他设备。

Codex 在会话启动时发现全局规则；若本机存在 `AGENTS.override.md`，先核对其覆盖关系。部署落盘不等于已有会话重新加载或行为效果已证明。加载机制见 [官方说明](https://learn.chatgpt.com/docs/agent-configuration/agents-md)。

## 验证边界

隔离测试覆盖首次部署、预演零写入、重复执行不重写、已有定制冲突保留、空目标初始化和无效源拒绝。实机只核对本机现有规则与共享源一致；不为此次入库启动 VM 或执行其他设备更新。跨项目行为效果留待正常工程任务观察。
