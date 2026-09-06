<#
.SYNOPSIS
    一键从 GitHub 拉取最新技能并自动挂载 (Pull & Auto-Mount)
.DESCRIPTION
    面向多机协同（从机/主机）的一键同步工具：
      1. 自动检测并临时暂存本地未提交更改 (git stash)，防止拉取中断
      2. 执行安全 rebase 拉取 (git pull --rebase origin main)
      3. 恢复本地暂存更改 (git stash pop)
      4. 自动调用 sync-skills.ps1，为新下载的技能自动建立 NTFS Junction 挂载并清理坏链
.PARAMETER NoSync
    仅拉取 Git 代码，不触发本地 Agent 挂载。
.PARAMETER Status
    同步完成后显示当前各 Agent 的挂载健康状态。
.EXAMPLE
    .\scripts\pull-sync.ps1
.EXAMPLE
    .\scripts\pull-sync.ps1 -Status
#>

[CmdletBinding()]
param(
    [switch]$NoSync,
    [switch]$Status
)

$ErrorActionPreference = "Stop"

$WorkspaceRoot = (Resolve-Path "$PSScriptRoot\..").Path
$SyncScript = Join-Path $WorkspaceRoot "scripts\sync-skills.ps1"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 🔄 技能库一键拉取与自动挂载 (Pull & Sync)" -ForegroundColor Cyan
Write-Host " 工作区路径: $WorkspaceRoot" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

Push-Location $WorkspaceRoot
try {
    # 1. 检查是否有本地脏状态
    $statusOutput = git status --porcelain
    $hasLocalChanges = ![string]::IsNullOrWhiteSpace($statusOutput)
    $stashed = $false

    if ($hasLocalChanges) {
        Write-Host "`n[1/3] 检测到本地存在未提交修改，正在临时暂存 (git stash)..." -ForegroundColor Yellow
        git stash save "auto-stash-pull-sync-$(Get-Date -Format 'yyyyMMdd-HHmmss')" | Out-Null
        $stashed = $true
        Write-Host "  ✓ 本地工作区已暂存保护。" -ForegroundColor Green
    } else {
        Write-Host "`n[1/3] 本地工作区干净，无需暂存。" -ForegroundColor Gray
    }

    # 2. 拉取远端更新
    Write-Host "`n[2/3] 从 GitHub 拉取最新技能 (git pull --rebase origin main)..." -ForegroundColor Yellow
    git pull --rebase origin main

    if ($stashed) {
        Write-Host "  正在恢复之前暂存的本地修改 (git stash pop)..." -ForegroundColor Yellow
        git stash pop | Out-Null
        Write-Host "  ✓ 本地暂存已恢复。" -ForegroundColor Green
    }

    # 3. 自动挂载各 Agent 目录
    if (!$NoSync) {
        Write-Host "`n[3/3] 自动更新各 Agent 挂载点 (sync-skills.ps1)..." -ForegroundColor Yellow
        if (Test-Path $SyncScript) {
            if ($Status) {
                & $SyncScript -Status
            } else {
                & $SyncScript
            }
        }
    } else {
        Write-Host "`n[3/3] 跳过本地挂载刷新 (-NoSync)" -ForegroundColor Gray
    }

    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host " 🎉 技能更新拉取与本地挂载已完成！" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan
} finally {
    Pop-Location
}
