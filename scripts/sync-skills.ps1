<#
.SYNOPSIS
    跨 Agent 与跨机器统一技能分发脚本 (Windows NTFS Junction)
.DESCRIPTION
    将 G:\agent-skills-workspace\skills (或当前仓库相对路径) 下的中央技能库
    以免提权的 NTFS Junction 软链接形式，挂载到本机所有 Coding Agent 的全局技能目录。
.PARAMETER DryRun
    仅预览将要执行的操作，不实际修改文件系统。
.PARAMETER Status
    检查并输出当前所有 Agent 的技能挂载状态与健康度。
.PARAMETER Force
    若目标存在旧版物理文件夹或冲突链接，自动备份并替换为 Junction。
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Status,
    [switch]$Force = $true
)

$ErrorActionPreference = "Stop"

# 1. 解析中央库路径 (优先相对于脚本自身目录，兼具跨机可移植性)
$WorkspaceRoot = (Resolve-Path "$PSScriptRoot\..").Path
$CentralSkillsDir = Join-Path $WorkspaceRoot "skills"

if (!(Test-Path $CentralSkillsDir)) {
    Write-Error "找不到中央技能目录: $CentralSkillsDir"
    exit 1
}

# 2. 定义支持的 Agent 目录映射
$UserHome = [System.Environment]::GetFolderPath("UserProfile")
$AgentTargets = @{
    "ChatGPT (Codex)"  = Join-Path $UserHome ".codex\skills"
    "Grok (grokbuild)" = Join-Path $UserHome ".grok\skills"
    "DeepSeek Harness" = Join-Path $UserHome ".dsh\skills"
    "Antigravity"                  = Join-Path $UserHome ".gemini\config\skills"
    "Antigravity (Skills Manager)" = Join-Path $UserHome ".gemini\antigravity\skills"
    "Claude Code"                  = Join-Path $UserHome ".claude\skills"
}

# 获取中央库中的有效技能目录列表
$CentralSkills = Get-ChildItem -Path $CentralSkillsDir -Directory | Where-Object {
    Test-Path (Join-Path $_.FullName "SKILL.md")
}

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 🚀 跨 Agent 统一技能同步与挂载工具 (NTFS Junction)" -ForegroundColor Cyan
Write-Host " 中央技能库: $CentralSkillsDir" -ForegroundColor Gray
Write-Host " 发现中央技能: $($CentralSkills.Count) 个 ($($CentralSkills.Name -join ', '))" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

# 辅助函数: 检查路径是否为坏死链接
function Test-BrokenLink($Path) {
    if (!(Test-Path $Path)) { return $false }
    $item = Get-Item -Path $Path -Force
    if ($item.LinkType -in @("SymbolicLink", "Junction")) {
        $target = $item.Target
        if ($target -and !(Test-Path $target)) {
            return $true
        }
    }
    return $false
}

# 3. 状态检查模式 (-Status)
if ($Status) {
    Write-Host "`n📊 [检查当前各 Agent 挂载状态]" -ForegroundColor Yellow
    foreach ($agentName in $AgentTargets.Keys | Sort-Object) {
        $targetDir = $AgentTargets[$agentName]
        Write-Host "`n[$agentName] -> $targetDir" -ForegroundColor White
        if (!(Test-Path $targetDir)) {
            Write-Host "  (目录不存在)" -ForegroundColor DarkGray
            continue
        }

        $items = Get-ChildItem -Path $targetDir -Force
        foreach ($skill in $CentralSkills) {
            $matched = $items | Where-Object { $_.Name -eq $skill.Name }
            if ($matched) {
                if ($matched.LinkType -eq "Junction") {
                    $isHealthy = (Test-Path $matched.Target)
                    $color = if ($isHealthy) { "Green" } else { "Red" }
                    $tag = if ($isHealthy) { "✓ 正常联接" } else { "✗ 坏死联接" }
                    Write-Host "  $tag : $($skill.Name) -> $($matched.Target)" -ForegroundColor $color
                } else {
                    Write-Host "  ! 物理副本: $($skill.Name) (非中央联接)" -ForegroundColor Yellow
                }
            } else {
                Write-Host "  - 未挂载 : $($skill.Name)" -ForegroundColor DarkGray
            }
        }
    }
    Write-Host "`n状态检查完成。" -ForegroundColor Cyan
    exit 0
}

# 4. 执行挂载与同步模式
$BackupBaseDir = Join-Path $WorkspaceRoot "backups\$(Get-Date -Format 'yyyyMMdd-HHmmss')"

foreach ($agentName in $AgentTargets.Keys | Sort-Object) {
    $targetDir = $AgentTargets[$agentName]
    Write-Host "`n------------------------------------------------------------" -ForegroundColor DarkGray
    Write-Host "🔧 正在同步 Agent: [$agentName]" -ForegroundColor Yellow
    Write-Host "   目标路径: $targetDir" -ForegroundColor Gray

    if (!(Test-Path $targetDir)) {
        if ($DryRun) {
            Write-Host "   [DryRun] 将创建目标技能目录: $targetDir" -ForegroundColor Magenta
        } else {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
            Write-Host "   已创建目标技能目录。" -ForegroundColor Gray
        }
    }

    # A. 扫描并清理现有的坏死链接 (Broken Junctions/Symlinks)
    if (Test-Path $targetDir) {
        $existingItems = Get-ChildItem -Path $targetDir -Force
        foreach ($item in $existingItems) {
            if ($item.LinkType -in @("SymbolicLink", "Junction")) {
                $target = $item.Target
                # 检查链接目标是否存在
                if (!$target -or !(Test-Path $target)) {
                    Write-Host "   ⚠️ 发现坏死链接: $($item.Name) -> $target" -ForegroundColor Red
                    if ($DryRun) {
                        Write-Host "      [DryRun] 将删除坏死链接: $($item.FullName)" -ForegroundColor Magenta
                    } else {
                        Remove-Item -Path $item.FullName -Force
                        Write-Host "      ✓ 已清理坏死链接。" -ForegroundColor Green
                    }
                }
            }
            # 清理历史遗留的 .old-link (若尚未被上述逻辑删除)
            if ((Test-Path $item.FullName) -and ($item.Name -like "*.old-link")) {
                Write-Host "   ⚠️ 发现历史残留链接: $($item.Name)" -ForegroundColor DarkYellow
                if ($DryRun) {
                    Write-Host "      [DryRun] 将删除残留链接: $($item.FullName)" -ForegroundColor Magenta
                } else {
                    Remove-Item -Path $item.FullName -Force
                    Write-Host "      ✓ 已删除残留链接。" -ForegroundColor Green
                }
            }
        }
    }

    # B. 逐个挂载中央技能 (NTFS Junction)
    foreach ($skill in $CentralSkills) {
        $skillName = $skill.Name
        $sourcePath = $skill.FullName
        $destPath = Join-Path $targetDir $skillName

        # 检查目标是否已存在
        if (Test-Path $destPath) {
            $destItem = Get-Item -Path $destPath -Force
            if ($destItem.LinkType -eq "Junction") {
                # 已经是联接点，检查目标是否正确
                $currentTarget = (Resolve-Path $destItem.Target -ErrorAction SilentlyContinue).Path
                $expectedTarget = (Resolve-Path $sourcePath).Path
                if ($currentTarget -eq $expectedTarget) {
                    Write-Host "   ✓ 已挂载且正常: $skillName" -ForegroundColor Green
                    continue
                } else {
                    Write-Host "   🔄 联接目标不一致: $skillName (当前: $currentTarget)" -ForegroundColor Yellow
                    if ($DryRun) {
                        Write-Host "      [DryRun] 将重新建立联接指向: $sourcePath" -ForegroundColor Magenta
                    } else {
                        Remove-Item -Path $destPath -Force
                        New-Item -ItemType Junction -Path $destPath -Target $sourcePath | Out-Null
                        Write-Host "      ✓ 已重定向联接。" -ForegroundColor Green
                    }
                    continue
                }
            } else {
                # 目标是物理文件夹或非 Junction 文件
                Write-Host "   ⚠️ 目标存在物理副本或普通文件: $skillName" -ForegroundColor Yellow
                if ($Force) {
                    if ($DryRun) {
                        Write-Host "      [DryRun] 将备份并替换为 Junction: $destPath" -ForegroundColor Magenta
                    } else {
                        $backupFolder = Join-Path $BackupBaseDir $agentName
                        if (!(Test-Path $backupFolder)) { New-Item -ItemType Directory -Path $backupFolder -Force | Out-Null }
                        $backupDest = Join-Path $backupFolder $skillName
                        Move-Item -Path $destPath -Destination $backupDest -Force
                        Write-Host "      已备份原副本至: $backupDest" -ForegroundColor Gray

                        New-Item -ItemType Junction -Path $destPath -Target $sourcePath | Out-Null
                        Write-Host "      ✓ 已挂载为中央库 Junction。" -ForegroundColor Green
                    }
                } else {
                    Write-Host "      跳过 (未指定 -Force，保留原文件)。" -ForegroundColor Gray
                }
                continue
            }
        }

        # 目标不存在，直接建立 Junction
        if ($DryRun) {
            Write-Host "   [DryRun] 将挂载: $skillName -> $sourcePath" -ForegroundColor Magenta
        } else {
            New-Item -ItemType Junction -Path $destPath -Target $sourcePath | Out-Null
            Write-Host "   ✓ 挂载成功: $skillName" -ForegroundColor Green
        }
    }
}

# 5. 配置 Antigravity 全局配置与工作区规范
Write-Host "`n------------------------------------------------------------" -ForegroundColor DarkGray
Write-Host "🔧 正在配置 Antigravity 全局与工作区规范..." -ForegroundColor Yellow

# A. 配置 ~/.gemini/config/skills.json (官方声明外部技能库)
$GeminiConfigDir = Join-Path $UserHome ".gemini\config"
if (!(Test-Path $GeminiConfigDir)) { New-Item -ItemType Directory -Path $GeminiConfigDir -Force | Out-Null }
$SkillsJsonPath = Join-Path $GeminiConfigDir "skills.json"
$formattedCentralPath = $CentralSkillsDir -replace '\\', '/'
$skillsJsonObj = @{
    entries = @(
        @{ path = $formattedCentralPath }
    )
}
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)
$skillsJsonText = $skillsJsonObj | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText($SkillsJsonPath, $skillsJsonText, $utf8NoBom)
Write-Host "   ✓ 已生成 Antigravity 全局技能索引: $SkillsJsonPath" -ForegroundColor Green

# B. 确保当前工作区规范 .agents/skills 联接
$WorkspaceAgentsDir = Join-Path $WorkspaceRoot ".agents"
if (!(Test-Path $WorkspaceAgentsDir)) { New-Item -ItemType Directory -Path $WorkspaceAgentsDir -Force | Out-Null }
$WorkspaceAgentsSkills = Join-Path $WorkspaceAgentsDir "skills"
if (!(Test-Path $WorkspaceAgentsSkills)) {
    New-Item -ItemType Junction -Path $WorkspaceAgentsSkills -Target $CentralSkillsDir | Out-Null
    Write-Host "   ✓ 已挂载工作区规范联接: $WorkspaceAgentsSkills -> $CentralSkillsDir" -ForegroundColor Green
} else {
    Write-Host "   ✓ 工作区规范联接正常: $WorkspaceAgentsSkills" -ForegroundColor Green
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host " 🎉 所有目标 Agent 的技能挂载与环境配置已处理完毕！" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
