<#
.SYNOPSIS
    跨 Agent 与跨机器统一技能分发脚本 (Windows NTFS Junction)
.DESCRIPTION
    将当前仓库 skills 下的中央技能库挂载到本机 Agent 的全局技能目录。
    不调用 Skills Manager、Git 或其他同步脚本；未登记链接不会被清理。
.PARAMETER DryRun
    仅预览，不创建目录、备份、联接或写入配置与规则。
.PARAMETER Status
    只读检查链接是否指向当前中央技能库。
.PARAMETER Force
    备份并替换冲突的物理副本或规则文件；未知链接始终保留。
.PARAMETER UserProfilePath
    可选的绝对用户根路径；未指定时使用系统 UserProfile。用于显式跨机配置或隔离测试。
#>

[CmdletBinding()]
param(
    [switch]$DryRun,
    [switch]$Status,
    [switch]$Force,
    [string]$UserProfilePath
)

$ErrorActionPreference = "Stop"
$script:Unresolved = [System.Collections.Generic.List[string]]::new()
$WorkspaceRoot = (Resolve-Path "$PSScriptRoot\..").Path
$CentralSkillsDir = Join-Path $WorkspaceRoot "skills"
if (!(Test-Path -LiteralPath $CentralSkillsDir -PathType Container)) {
    throw "找不到中央技能目录: $CentralSkillsDir"
}

function Get-NormalPath([string]$Path) {
    $fullPath = [System.IO.Path]::GetFullPath($Path)
    if ($fullPath -eq [System.IO.Path]::GetPathRoot($fullPath)) { return $fullPath }
    return $fullPath.TrimEnd('\', '/')
}
function Get-Entry([string]$Path) {
    return Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
}
function Test-Reparse($Item) {
    return $null -ne $Item -and (($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) -ne 0)
}
function Get-LinkTarget($Item) {
    if (!(Test-Reparse $Item) -or $Item.LinkType -notin @('Junction', 'SymbolicLink')) { return $null }
    $targets = @($Item.Target)
    if ($targets.Count -ne 1 -or !$targets[0]) { return $null }
    $target = [string]$targets[0]
    if (![System.IO.Path]::IsPathRooted($target)) { $target = Join-Path (Split-Path -Parent $Item.FullName) $target }
    return Get-NormalPath $target
}
function Test-OwnedLink($Item, [string]$Source) {
    return (Test-Reparse $Item) -and ((Get-LinkTarget $Item) -eq (Get-NormalPath $Source))
}
function Report-Conflict([string]$Message) {
    $script:Unresolved.Add($Message)
    Write-Warning $Message
}

# All writes stay below an explicit physical root. Never follow an agent root/parent junction.
function Test-SafeDirectory([string]$Path, [string]$Root) {
    $rootPath = Get-NormalPath $Root
    $fullPath = Get-NormalPath $Path
    if ($fullPath -ne $rootPath -and !$fullPath.StartsWith($rootPath.TrimEnd('\', '/') + '\', [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "路径超出允许根目录: $fullPath (根: $rootPath)"
    }
    $probe = $fullPath
    while ($true) {
        $item = Get-Entry $probe
        if ($item -and ((Test-Reparse $item) -or !$item.PSIsContainer)) {
            Report-Conflict "保留非物理目录边界，跳过: $probe"
            return $false
        }
        if ($probe -eq $rootPath) { break }
        $probe = Split-Path -Parent $probe
    }
    return $true
}
function Ensure-Directory([string]$Path, [string]$Root) {
    if (!(Test-SafeDirectory $Path $Root)) { return $false }
    if (!(Get-Entry $Path)) {
        if ($DryRun) { Write-Host "[DryRun] 将创建目录: $Path" }
        else { New-Item -ItemType Directory -Path $Path -Force | Out-Null }
    }
    return $true
}

if ($PSBoundParameters.ContainsKey('UserProfilePath')) {
    if ([string]::IsNullOrWhiteSpace($UserProfilePath) -or $UserProfilePath -notmatch '^(?:[A-Za-z]:[\\/]|\\\\[^\\]+\\[^\\]+)') {
        throw 'UserProfilePath 必须是绝对路径。'
    }
    $UserHome = Get-NormalPath $UserProfilePath
} else {
    $UserHome = Get-NormalPath ([System.Environment]::GetFolderPath('UserProfile'))
}

# Keep the existing product mappings; no manager CLI or machine-local database is consulted.
$AgentTargets = @{
    'ChatGPT (Codex)' = Join-Path $UserHome '.codex\skills'
    'Grok (grokbuild)' = Join-Path $UserHome '.grok\skills'
    'DeepSeek Harness' = Join-Path $UserHome '.dsh\skills'
    'Antigravity' = Join-Path $UserHome '.gemini\config\skills'
    'Antigravity (Skills Manager)' = Join-Path $UserHome '.gemini\antigravity\skills'
    'Claude Code' = Join-Path $UserHome '.claude\skills'
}
$SkillTargetFilters = @{
    'progress-brief' = @('Antigravity', 'Antigravity (Skills Manager)', 'Grok (grokbuild)')
}
$CentralSkills = @(Get-ChildItem -LiteralPath $CentralSkillsDir -Directory | Where-Object {
    !(Test-Reparse $_) -and (Test-Path -LiteralPath (Join-Path $_.FullName 'SKILL.md') -PathType Leaf)
})
Write-Host "中央技能库: $CentralSkillsDir ($($CentralSkills.Count) 个技能)"

if ($Status) {
    foreach ($agentName in $AgentTargets.Keys | Sort-Object) {
        $targetDir = $AgentTargets[$agentName]
        Write-Host "`n[$agentName] -> $targetDir"
        if (!(Test-SafeDirectory $targetDir $UserHome)) { continue }
        foreach ($skill in $CentralSkills) {
            $allowed = !$SkillTargetFilters.ContainsKey($skill.Name) -or $agentName -in $SkillTargetFilters[$skill.Name]
            $item = Get-Entry (Join-Path $targetDir $skill.Name)
            if (!$allowed) { Write-Host "[已排除] $($skill.Name); 当前存在: $($null -ne $item)" }
            elseif (Test-OwnedLink $item $skill.FullName) { Write-Host "[正常联接] $($skill.Name)" }
            elseif ($item) { Write-Host "[冲突/非中央联接] $($skill.Name) -> $(Get-LinkTarget $item)" }
            else { Write-Host "[未挂载] $($skill.Name)" }
        }
    }
    Write-Host '状态检查完成（只读）。'
    exit 0
}

$BackupBaseDir = Join-Path $WorkspaceRoot ("backups\sync-" + (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + [guid]::NewGuid().ToString('N'))
function Save-FileBackup([string]$Path, [string]$Label) {
    $backupDir = Join-Path $BackupBaseDir $Label
    if (!(Ensure-Directory $backupDir $WorkspaceRoot)) { throw "备份目录不可用: $backupDir" }
    if (!$DryRun) {
        $backupPath = Join-Path $backupDir (Split-Path -Leaf $Path)
        Copy-Item -LiteralPath $Path -Destination $backupPath
        @{ original = $Path; backup = $backupPath; kind = 'file-copy' } | ConvertTo-Json |
            Set-Content -LiteralPath ($backupPath + '.restore.json') -Encoding UTF8
    }
}
function Save-LinkBackup($Item, [string]$Source, [string]$Label) {
    if (!(Test-OwnedLink $Item $Source)) { throw "拒绝解除未知链接: $($Item.FullName)" }
    $backupDir = Join-Path $BackupBaseDir $Label
    if (!(Ensure-Directory $backupDir $WorkspaceRoot)) { throw "备份目录不可用: $backupDir" }
    if (!$DryRun) {
        @{ original = $Item.FullName; target = Get-LinkTarget $Item; link_type = $Item.LinkType } |
            ConvertTo-Json | Set-Content -LiteralPath (Join-Path $backupDir ($Item.Name + '.link.json')) -Encoding UTF8
    }
}
function Remove-OwnedLink([string]$Path, [string]$Source, [string]$Root, [string]$Label) {
    if (!(Test-SafeDirectory (Split-Path -Parent $Path) $Root)) { return }
    $item = Get-Entry $Path
    if (!(Test-OwnedLink $item $Source)) { throw "拒绝解除未知链接: $Path" }
    if ($DryRun) { Write-Host "[DryRun] 将备份并解除自有链接: $Path"; return }
    Save-LinkBackup $item $Source $Label
    if ($item.PSIsContainer) { [System.IO.Directory]::Delete($Path, $false) }
    else { [System.IO.File]::Delete($Path) }
}
function Test-PhysicalTree([string]$Path) {
    $item = Get-Entry $Path
    if (Test-Reparse $item) { return $false }
    if ($item.PSIsContainer) {
        foreach ($child in Get-ChildItem -LiteralPath $Path -Force) {
            if (!(Test-PhysicalTree $child.FullName)) { return $false }
        }
    }
    return $true
}
function Mount-Skill([string]$Dest, [string]$Source, [string]$Root, [string]$Label) {
    if (!(Test-SafeDirectory (Split-Path -Parent $Dest) $Root)) { return }
    $item = Get-Entry $Dest
    if (Test-OwnedLink $item $Source) { Write-Host "[正常联接] $Dest"; return }
    if ($item) {
        if (Test-Reparse $item) { Report-Conflict "保留未知链接（包括 -Force）: $Dest"; return }
        if (!$Force) { Report-Conflict "保留物理副本；如需备份替换请显式指定 -Force: $Dest"; return }
        if (!(Test-PhysicalTree $Dest)) { Report-Conflict "保留含链接的物理副本，需单独审查: $Dest"; return }
        $backupDir = Join-Path $BackupBaseDir $Label
        $backupDest = Join-Path $backupDir (Split-Path -Leaf $Dest)
        if (!(Ensure-Directory $backupDir $WorkspaceRoot)) { throw "备份目录不可用: $backupDir" }
        if ($DryRun) { Write-Host "[DryRun] 将备份 $Dest 至 $backupDest 并挂载 $Source"; return }
        # Both final absolute paths and their parents have been checked; never recursively delete a physical copy.
        Move-Item -LiteralPath $Dest -Destination $backupDest
        @{ original = $Dest; backup = $backupDest; kind = 'physical-move' } | ConvertTo-Json |
            Set-Content -LiteralPath ($backupDest + '.restore.json') -Encoding UTF8
        Write-Host "已备份物理副本: $backupDest"
    }
    if ($DryRun) { Write-Host "[DryRun] 将挂载: $Dest -> $Source" }
    else { New-Item -ItemType Junction -Path $Dest -Target $Source | Out-Null }
}

foreach ($agentName in $AgentTargets.Keys | Sort-Object) {
    $targetDir = $AgentTargets[$agentName]
    Write-Host "`n[$agentName] -> $targetDir"
    if (!(Ensure-Directory $targetDir $UserHome)) { continue }
    # Only names present in the central library are managed. Unrelated/broken/*.old-link entries are untouched.
    foreach ($skill in $CentralSkills) {
        $destPath = Join-Path $targetDir $skill.Name
        $allowed = !$SkillTargetFilters.ContainsKey($skill.Name) -or $agentName -in $SkillTargetFilters[$skill.Name]
        if (!$allowed) {
            $item = Get-Entry $destPath
            if (Test-OwnedLink $item $skill.FullName) { Remove-OwnedLink $destPath $skill.FullName $UserHome $agentName }
            elseif ($item) { Write-Warning "保留排除名称下的非自有内容: $destPath" }
            continue
        }
        Mount-Skill $destPath $skill.FullName $UserHome $agentName
    }
}

# Antigravity compatibility index: merge entries, preserve unrelated settings, back up any changed original.
$GeminiConfigDir = Join-Path $UserHome '.gemini\config'
$SkillsJsonPath = Join-Path $GeminiConfigDir 'skills.json'
if (Ensure-Directory $GeminiConfigDir $UserHome) {
    $indexItem = Get-Entry $SkillsJsonPath
    $indexValid = $true
    $indexObject = [pscustomobject]@{ entries = @() }
    if ($indexItem) {
        if ((Test-Reparse $indexItem) -or $indexItem.PSIsContainer) {
            Report-Conflict "保留非普通索引文件: $SkillsJsonPath"
            $indexValid = $false
        } else {
            try {
                $indexObject = Get-Content -LiteralPath $SkillsJsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
                if ($null -eq $indexObject -or $indexObject -isnot [pscustomobject]) { throw '索引根必须是对象' }
                if ($indexObject.PSObject.Properties['entries'] -and $indexObject.entries -isnot [System.Array]) { throw 'entries 必须是数组' }
                if (!$indexObject.PSObject.Properties['entries']) { $indexObject | Add-Member -NotePropertyName entries -NotePropertyValue @() }
            } catch {
                Report-Conflict "保留无法合并的索引 $SkillsJsonPath : $_"
                $indexValid = $false
            }
        }
    }
    if ($indexValid) {
        $formattedCentralPath = $CentralSkillsDir -replace '\\', '/'
        $hasEntry = @($indexObject.entries | Where-Object {
            $_.path -and (([string]$_.path -replace '\\', '/').TrimEnd('/') -eq $formattedCentralPath)
        }).Count -gt 0
        if (!$hasEntry) {
            $indexObject.entries = @($indexObject.entries) + @([pscustomobject]@{ path = $formattedCentralPath })
            if ($indexItem -and !$Force) { Report-Conflict "保留索引差异；如需备份合并请显式指定 -Force: $SkillsJsonPath" }
            elseif ($DryRun) { Write-Host "[DryRun] 将合并全局技能索引: $SkillsJsonPath" }
            else {
                if ($indexItem) { Save-FileBackup $SkillsJsonPath 'Antigravity-index' }
                [System.IO.File]::WriteAllText($SkillsJsonPath, ($indexObject | ConvertTo-Json -Depth 100), [System.Text.UTF8Encoding]::new($false))
            }
        }
    }
}

$WorkspaceAgentsDir = Join-Path $WorkspaceRoot '.agents'
if (Ensure-Directory $WorkspaceAgentsDir $WorkspaceRoot) {
    Mount-Skill (Join-Path $WorkspaceAgentsDir 'skills') $CentralSkillsDir $WorkspaceRoot 'workspace-agents'
}

# Existing rule conflicts are preserved by default; Force backs up ordinary files before replacement.
$CentralAgentsRule = Join-Path $WorkspaceRoot 'rules\AGENTS.md'
if (Test-Path -LiteralPath $CentralAgentsRule -PathType Leaf) {
    $ruleDirs = @((Join-Path $GeminiConfigDir 'rules'), (Join-Path $UserHome '.grok\rules'))
    foreach ($ruleDir in $ruleDirs) {
        if (!(Ensure-Directory $ruleDir $UserHome)) { continue }
        $rulePath = Join-Path $ruleDir 'AGENTS.md'
        $ruleItem = Get-Entry $rulePath
        if ($ruleItem) {
            if ((Test-Reparse $ruleItem) -or $ruleItem.PSIsContainer) { Report-Conflict "保留非普通规则文件: $rulePath"; continue }
            if ((Get-FileHash -LiteralPath $rulePath).Hash -eq (Get-FileHash -LiteralPath $CentralAgentsRule).Hash) { continue }
            if (!$Force) { Report-Conflict "保留规则冲突；如需备份替换请显式指定 -Force: $rulePath"; continue }
        }
        if ($DryRun) { Write-Host "[DryRun] 将备份（若存在）并分发规则: $rulePath" }
        else {
            if ($ruleItem) {
                $label = if ($ruleDir -eq $ruleDirs[0]) { 'Antigravity-rules' } else { 'Grok-rules' }
                Save-FileBackup $rulePath $label
            }
            Copy-Item -LiteralPath $CentralAgentsRule -Destination $rulePath
        }
    }
}
if ($script:Unresolved.Count -gt 0 -and !$DryRun) {
    Write-Warning "同步未完成：$($script:Unresolved.Count) 项冲突已保留。仓库内容可能已更新，但相应 Agent 入口仍需处理。"
    exit 2
}
if ($DryRun) { Write-Host '`n预览完成（未写入）；请检查上方保留/冲突提示。' }
else { Write-Host '`n技能挂载与配置处理完成。' }
