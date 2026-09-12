---
type: project_topic
authoring_mode: ai_generated
contains: [decision, lesson]
---

# Codex 委派策略同步

共享源为 [`config/codex/delegation-policy.txt`](../config/codex/delegation-policy.txt)，应用入口为 [`scripts/sync-codex-policy.py`](../scripts/sync-codex-policy.py)。Git 分发策略和脚本，各设备显式更新自身 `config.toml` 中的 `features.multi_agent_v2.multi_agent_mode_hint_text`。技能入口、Skills Manager 和 MCP 不参与此流程；普通 pull 仍只更新仓库。

## 使用

需要 Python 3.11+。应用仅支持 Windows，使用系统 Windows PowerShell 设置备份权限。配置依据本机 `CODEX_HOME`，未设置时使用用户目录下的 `.codex`。先核对桌面正在使用的实际 `codex.exe`；PATH CLI 可能是另一个版本。

在仓库根运行：

```powershell
# 状态检查：不写文件，不启动 Codex 探针。
python scripts/sync-codex-policy.py

# 把此变量设为该设备核实过的 Codex 运行时绝对路径。
$codexRuntime = 'C:\path\to\actual\codex.exe'

# 临时隔离配置中检查完整提示；不修改用户配置。
python scripts/sync-codex-policy.py --dry-run --codex $codexRuntime

# 备份、仅更新目标键，再核验真实配置的完整提示。
python scripts/sync-codex-policy.py --apply --codex $codexRuntime
```

预演会创建并清理临时文件。应用时持有 Windows 文件写入锁，阻止另一写入者或替换操作，允许提示核验读取。备份先设置并核对 ACL，再写入原配置。目标原位更新以保留权限；正常异常在同一锁内恢复。强杀进程或断电后可能需要从同目录 `config.toml.bak-delegation-*` 备份恢复，恢复前比较后来新增的设置。

脚本不输出原配置、凭据或提示原文，也不把备份放进 Git。默认仅报告是否匹配和策略哈希。重复应用已匹配的策略只验证，不重写。多行目标值、特殊 TOML 布局、标量开关、符号链接及缺失配置等未经支持的情况保留原文件并退出；不能为部署成功重写整个配置。目标赋值行会规范化并移除该行尾注释，其他设置通过解析前后比较保护。

新进程提示通过不代表长期运行的桌面 app-server 已刷新；方便时重启并以新任务核验。脚本不自动关闭用户正在执行的任务。

## 决策与经验

- 通用委派/监控偏好属于 Codex 配置；项目 `AGENTS.md` 补充项目耗时与异常标准，复杂操作流程才另做 Skill。
- 2026-09-12 本机曾观察到较长 hint 在提示中间出现截断标记，五分钟检查所在段落受影响。现已缩短共享策略；运行时核验要求策略全文出现，不能仅凭前后文匹配断言完整生效。
- Surface 的历史记录曾显示桌面 bundled CLI 与 PATH CLI 不同，因此必须传入每台设备确认过的实际二进制，而非按另一台机器版本推断兼容。
- `--strict-config` 不能假定适用于每个调试子命令；此入口用实际 `debug prompt-input` 证明目标键被读取且完整进入提示。
- Windows PowerShell 从 PowerShell 7 继承模块路径时可能无法加载 Security 模块；备份 ACL 子进程移除继承的 `PSModulePath`，由 Windows PowerShell 建立自身默认路径。
- ACL 验证比较 owner、group、保护状态和 ACE，而不把无关的自动继承标志序列化差异当作权限变化。

## 验证范围

`tests/test_codex_policy.py` 覆盖配置范围、复杂布局拒绝、幂等、备份、回滚、Windows 并发写入及完整提示判断。持续集成使用合成配置，不读取开发者的真实配置，也不依赖已登录的 Codex。每台设备部署时再执行真实运行时预演、应用及重复应用核验。

设备部署结果属于当次快照。策略哈希相同证明内容一致；尚不能证明以后自动拉取或自动应用。后续更新仍需各设备显式拉取并应用。
