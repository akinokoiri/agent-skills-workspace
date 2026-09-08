---
type: project_topic
status: active
summary: "Git 同步中央内容；本机入口只选择一个管理器，来源登记和凭据不随库分发。"
tags: [skills, git, synchronization]
contains: [decision, lesson]
created: "2026-09-08"
updated: "2026-09-08"
related: [rule-skill-repair-2026-09-08.md]
authoring_mode: ai_generated
---
# 技能多机同步契约

## 已确认的来源与职责

用户确认 `akinokoiri/agent-skills-workspace` 是通用技能多机同步库。Git 管正文与规则；酒店业务技能保持项目/百度共享来源；Skills Manager 的数据库、认证、预设与部署记录是各设备本机状态。

本轮审查时已核对 Skills Manager 1.37.0 的 10 项中央技能与 60 个 symlink 目标，均解析回本仓库。当时旧 source_ref 指向已删除的临时导入目录；它影响来源预览/更新检查，不阻断既有联接读取 Git 更新后的正文。来源修正须在远端已包含当前内容后，用官方 `set-source` 做无内容替换迁移并逐条核验，保持本机备份；实际迁移结果以本次任务交付报告为准。

默认 `pull-sync` 和 `import-skill` 不调用任何挂载工具或 Skills Manager。脚本管理的设备按需显式 `-Sync`；Skills Manager 管理的设备用自己的预设维护入口。GUI 启动仍可能恢复活动预设，因此取消隐式 CLI 调用不意味着 GUI 只读。

## 失败与冲突处理

- 拉取前要求干净 main 和正确跟踪，只快进；不猜测哪个 stash 属于本任务，不自动回退/丢弃本机修改。
- 导入和 Git 步骤分别检查原生退出状态。无效 YAML、空描述和目录名称不一致在导入前失败；只有明确 -Push 才上传。
- 挂载预演不写入；默认保留物理副本、规则差异和未知链接。明确 -Force 替换普通副本时先备份；实际未解决冲突返回非零。
- setup 只包装技能入口配置，不重写 SM 配置、批量导入临时目录或注入 MCP。旧脚本里强制部署与吞掉失败后的“全部就绪”文字已移除。

## 验证与教训

验证覆盖原生命令失败传播、本地 Git remote 的拉取/导入/推送场景、隔离用户根下的预演与实体保护、setup 转发和失败返回。测试不调用真实 Skills Manager。提交前以实际测试结果与远端提交核对验收，其他设备的实际状态不能由本机测试推断。

上一轮基线意外调用真实 CLI 说明：其初始化先于子命令，即使 dry-run 也会写 DB/锁/缓存。真实来源迁移属于明确的受控操作，执行前备份数据库及元数据；不把它混入测试。

本机首次来源预检中，数据库 60 条显式 true 工具记录变为空表，备份和当前预设元数据原本都为 `tools: {}`。v1.37.0 的部署与 GUI 读取入口都会先对可用工具补默认 true；实际联接、成员顺序和有效选择未变。迁移检查仅允许这组已核实的表示转换，仍拒绝任何 false、新键、成员、设置或目标变化；不通过恢复整库或重新部署掩盖它。其他设备须先核对自身元数据，不能套用此例外。

跨设备测试应解析实际临时根路径后再作字符串与范围断言。GitHub Windows runner 的 `RUNNER~1` 和完整用户名可能指向同一目录；不能把路径拼写差异判为越界，也不能取消范围保护。远端 CI 的结果与本地通过结果分别记录。

上一次将 domain-modeling/SKILL.md 放进 references 仍被宿主递归发现，证明“内部目录”不等于不可发现。本轮改为 domain-modeling.md 并保留路由；通过目录枚举核验未增加新技能入口。

## 上游依据

- [Skills Manager v1.37.0](https://github.com/xingkongliang/skills-manager/tree/v1.37.0)。
- [CLI 来源修改接口](https://github.com/xingkongliang/skills-manager/blob/v1.37.0/src-tauri/src/bin/skills-manager-cli.rs#L189)。
- [部署读取中央路径](https://github.com/xingkongliang/skills-manager/blob/v1.37.0/src-tauri/src/core/scenario_service.rs#L83)。
- [GUI 启动恢复活动预设](https://github.com/xingkongliang/skills-manager/blob/v1.37.0/src-tauri/src/core/scenario_service.rs#L601)。
- [工具默认值](https://github.com/xingkongliang/skills-manager/blob/v1.37.0/src-tauri/src/core/skill_store.rs#L904)及 [GUI 读取前补默认值](https://github.com/xingkongliang/skills-manager/blob/v1.37.0/src-tauri/src/commands/sync.rs#L204)。

具体设备版本、提交和来源迁移结果保存在本次 Codex 任务交付报告；后续使用以就地核对为准。
