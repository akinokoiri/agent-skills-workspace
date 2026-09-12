# 跨设备技能库

通用技能与规则的 Git 来源是 [akinokoiri/agent-skills-workspace](https://github.com/akinokoiri/agent-skills-workspace)。各设备克隆本仓库，修改经审查、提交和推送后，由其他设备拉取。联接指向本机实际克隆路径，不能复制另一台机器的盘符。

## 文件来源与本机管理

| 内容 | 权威位置与同步方式 |
|---|---|
| 通用技能正文与配套参考 | 本仓库 `skills/`，通过 Git 同步。 |
| 通用行为规则 | 本仓库 `rules/AGENTS.md`；宿主已有定制文件发生差异时先保留。 |
| Codex 委派与监控策略 | `config/codex/delegation-policy.txt`，Git 拉取后显式运行 `scripts/sync-codex-policy.py` 合入本机配置；见[使用说明](cairn/codex-policy-sync.md)。 |
| 酒店业务技能 | 对应项目或百度共享源；不因本仓库更新而自动迁移入库。 |
| Skills Manager 数据库、预设、部署记录和认证 | 各设备本机状态，Git 忽略；不把另一台机器的数据库或密钥复制过来。 |

[Skills Manager](https://github.com/xingkongliang/skills-manager) 是独立的管理工具。本次核对版本为 1.37.0。它的 `skills sync` 会实际部署技能；GUI 启动也可能恢复活动预设，不能把它当作只读刷新命令。现有联接已指向中央技能目录时，Git 更新正文即可透过联接读取；客户端已加载的上下文仍可能需要重新加载。

每个设备选一种入口管理方式：已有 Skills Manager 管理的设备用它维护预设和部署；使用仓库脚本的设备通过 `sync-skills.ps1` 管理。普通拉取和导入默认都不部署入口，避免两个管理器轮流恢复同一批目录。

## 其他设备第一次更新到本次修复

先进入那台设备现有的仓库根，使用 Git 原生命令更新旧同步脚本：

```powershell
git status --short
# 上一条有输出时，先检查并保存本机改动，再继续。
git pull --ff-only
```

如果分支分叉或有会被覆盖的本地改动，保留现场并比较两边；不自动 reset、rebase 或弹出某个旧 stash。

此后日常更新使用修复后的入口：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\pull-sync.ps1
```

它要求工作区干净，在 `main` 及正确的 `origin/main` 跟踪关系下只做快进拉取；失败立即停止，不隐式调用 Skills Manager、挂载脚本或 MCP。`-Status` 只检查本地状态，不拉取；`-NoSync` 保留为兼容写法。

已有联接通常不必重装技能。只有选择脚本管理入口、且需要补建新入口时，显式运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-skills.ps1 -DryRun
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\sync-skills.ps1
```

预演不写文件。普通同步保留不同的物理副本、规则和未知链接；实际同步未解决必要冲突时返回非零。`-Force` 仅在比较差异并决定替换后使用，会先备份普通副本；未知链接仍保留。技能正文可能已经由 Git 更新，但某个本机副本未更新，须按逐项结果判断。

## 在本机修改并上传

1. 编辑本仓库中的目标文件；原样搬运用文件复制，内容审查读取必要正文。
2. 检查 `git diff`，运行相关验证，明确要提交的路径。保留其他任务改动。
3. `git add <已审查路径>`，随后 `git commit` 和 `git push origin main`。推送被拒绝时先取回并比较远端差异，不强推。

从本地目录导入：

```powershell
.\scripts\import-skill.ps1 -SourcePath "C:\path\to\skill"
# 明确要提交并上传该项导入时使用 -Push；导入前要求仓库干净。
.\scripts\import-skill.ps1 -SourcePath "C:\path\to\skill" -Push
```

导入默认不部署入口。`-Push` 在快进拉取后还要求 HEAD 与 origin/main 一致，避免把此前未发布的本地提交顺带上传；这些提交应先单独审查和发布。只有脚本管理的设备按需加 `-Sync`；`-Name` 必须与技能声明一致，不能仅改目录名。`-Force` 明确选择覆盖同名技能前先审查和备份。

## 新设备与 Skills Manager

新机先克隆并认证本仓库。脚本管理的设备运行 `scripts/setup-device.ps1`；`-StatusOnly` 只读，`-DryRun` 预演，默认不强制替换。该入口不配置 MCP、不改 Skills Manager 的 repo-config 或预设，也不通过临时目录批量安装。

Skills Manager 管理的设备单独配置其中央位置与所需目标。现有技能若登记为已删除的临时来源，可在备份后使用 v1.37.0 的 `skills set-source` 指向本仓库及 `skills/<name>`，保留 ID 与预设。先确认远端包含本地修改；不以 `--force` 掩盖内容差异。该 CLI 即使 `--dry-run` 也会初始化数据库/缓存，不能用于“零写入”测试。

本仓库根已有 `.git`，不为 Skills Manager 自动备份另建 `skills/.git` 或把不同目录结构盲接同一远端。Git 上传的是文件版本；本机来源登记、工具开关和预设不会随 Git 自动迁移。

## 验证与记录

```powershell
python -m pip install -r requirements-dev.txt
python scripts/validate-skills.py
python -m unittest discover -s tests -v
```

结构检查验证真实 YAML 和非空字段。Windows 行为测试使用临时仓库、临时用户目录和本地 Git remote；不运行真实 Skills Manager。导入、拉取和挂载分别检查退出状态，不能用“命令已调用”代替完成。

当前运行约束见 [AGENTS.md](AGENTS.md)，同步设计与验证边界见 [同步契约](cairn/skill-sync-contract.md)，历史变更见 [cairn/LOG.md](cairn/LOG.md)。
