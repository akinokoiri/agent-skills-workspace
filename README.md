# Agent Skills Workspace · 自用项目

自用的 Agent 技能、规则与多设备同步项目。包含从外部收集的技能，以及通过 AI 协助整理、修改和迭代的脚本与文档。

配置和默认策略按个人使用习惯维护，主要在自己的 Windows 设备上验证。仓库中的设备路径、工具版本和历史记录对应当时的使用环境，更新时仍需核对本机情况。

通用技能与规则的 Git 来源是 [akinokoiri/agent-skills-workspace](https://github.com/akinokoiri/agent-skills-workspace)。各设备克隆本仓库，修改经审查、提交和推送后，由其他设备拉取。联接指向本机实际克隆路径，不能复制另一台机器的盘符。

## 给执行更新的 Agent

在 Codex 中，用户要求“更新/同步本仓库 skills”时，默认完成本机的**技能更新、Codex 委派策略与专用规则同步**，按下面的顺序执行。用户明确限定只查看、只拉取 Git、只更新某个技能或不改配置时，遵循其限定；单纯读取本 README 不构成执行更新的请求。其他客户端只处理其适用的技能入口，不改 Codex 配置。

1. **定位本机。** 确认实际仓库、origin、分支和未提交改动；保留本机定制，工作区干净且跟踪正确的 `origin/main` 时才快进拉取。第一次使用先按下方“新设备与 Skills Manager”建立本机入口，不照搬其他设备的盘符、用户名或配置文件。
2. **更新技能正文并核验入口。** 拉取后重新读取 `AGENTS.md` 及本节，检查现有入口能读到新版。已联接本机仓库的入口无需重装；缺失、物理副本或冲突按设备既有管理方式处理，不能轮流调用两个管理器或自动覆盖定制。
3. **在 Codex 中同步策略。** 阅读 [Codex 策略同步说明](cairn/codex-policy-sync.md)。由 Agent 定位实际桌面/CLI 运行时，核对 Python 3.11+；桌面捆绑的 `codex.exe` 可能与 PATH CLI 不同。应用脚本目前仅支持 Windows；条件不满足时保留配置并报告此项未完成，不盲目安装依赖或绕过校验。
4. **同步 Codex 专用规则。** 运行 `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync-codex-rules.ps1`。默认使用 `CODEX_HOME`，未设置时用用户目录下的 `.codex`；缺失或空规则文件会复制，已一致则不重写，本机内容不同则保留并返回冲突。比较差异后合并，不能直接覆盖设备定制；操作方式见 [Codex 执行规则](cairn/codex-execution-rules.md)。
5. **分别验收。** 报告仓库提交、技能入口、策略哈希及完整提示验证结果，以及专用规则是否部署或存在冲突。Git 拉取成功不代表配置已应用；任务显示“完成”但拿不到结果也不算验收。需要时提醒重启 Codex 以刷新已加载的配置，不自动中断其他任务。

确认设备条件后，在仓库根执行策略步骤；`$codexRuntime` 由 Agent 填入该设备核实过的可执行文件绝对路径：

```powershell
python scripts/sync-codex-policy.py --dry-run --codex $codexRuntime
if ($LASTEXITCODE -ne 0) { throw '策略预演失败，保留本机配置并检查原因。' }
python scripts/sync-codex-policy.py --apply --codex $codexRuntime
if ($LASTEXITCODE -ne 0) { throw '策略应用未通过验证，按脚本结果检查恢复状态。' }
```

脚本会备份并只合入目标策略键、核验完整提示；重复执行已匹配的策略不会重写。不要复制整份 `config.toml`、认证、MCP 凭据或 Skills Manager 数据库，也不要把配置备份提交到 Git。状态检查与失败边界见上述策略说明。

这是 Agent 接到更新请求后的完整流程；`pull-sync.ps1` 本身仍只拉取 Git，不隐式部署配置。连接问题按已确认的本机工具和目标排查：不能因主机名无法解析或 ICMP 探测失败就断言 SSH 不可用；必要时可通过可信设备传输已核对发布提交与哈希的 Git bundle，并继续做快进与部署验收。

## 文件来源与本机管理

| 内容 | 权威位置与同步方式 |
|---|---|
| 通用技能正文与配套参考 | 本仓库 `skills/`，通过 Git 同步。 |
| Gemini／Grok 行为规则 | 本仓库 `rules/AGENTS.md`；由 `sync-skills.ps1` 分发，已有定制文件发生差异时先保留。 |
| Codex 工程执行规则 | `rules/codex/AGENTS.md`；通过 `scripts/sync-codex-rules.ps1` 部署到本机全局 `AGENTS.md`，不同内容保留待合并。 |
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

## 内容来源与许可

本仓库是自用的收集与维护集合，内容并非全部原创。`skills/project-cairn/` 来源于 [iBlinkQ/project-cairn](https://github.com/iBlinkQ/project-cairn)，保留其 [MIT 许可与版权说明](skills/project-cairn/LICENSE)，并包含本机使用过程中形成的修改。

其他技能的上游来源与许可尚未在本仓库中逐项注明。已有的版权与许可说明按对应文件保留；本仓库没有为全部内容统一声明许可，也不把收集的内容标为维护者原创。
