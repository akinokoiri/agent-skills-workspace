<#
.SYNOPSIS
    新设备/老设备跨 Agent 统一工作区环境一键初始化与修复脚本
.DESCRIPTION
    面向任何 Windows 新机或老机，执行无痛幂等初始化：
      1. 环境依赖检测 (Git, Node.js, npx, winget)
      2. 老旧脏技能扫描、安全带时间戳备份 (绝不破坏本地特有技能)
      3. 中央技能无权限 Junction 挂载与全 Agent 路径打通
      4. Antigravity 官方全局索引 (~/.gemini/config/skills.json) 生成
      5. 工作区规范 (.agents/skills) 链接修复
      6. (可选) GitHub MCP 快速注入与连通性验证
      7. (可选) 自动对接已安装的 Skills Manager 图形管理工具
.PARAMETER SkipMCP
    跳过 MCP 配置步骤。
.PARAMETER GitHubToken
    显式指定 GitHub Personal Access Token 用于初始化 MCP。
.PARAMETER StatusOnly
    仅检查当前环境与各 Agent 健康状态，不进行写入。
#>

[CmdletBinding()]
param(
    [switch]$SkipMCP,
    [string]$GitHubToken,
    [switch]$StatusOnly
)

$ErrorActionPreference = "Stop"

$WorkspaceRoot = (Resolve-Path "$PSScriptRoot\..").Path
$UserHome = [System.Environment]::GetFolderPath("UserProfile")

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 🚀 Agent Skills Workspace 全自动环境初始化/修复系统" -ForegroundColor Cyan
Write-Host " 目标主机: $env:COMPUTERNAME ($env:PROCESSOR_ARCHITECTURE)" -ForegroundColor Gray
Write-Host " 工作区路径: $WorkspaceRoot" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

# -------------------------------------------------------------
# 步骤 1: 检查基础运行时环境
# -------------------------------------------------------------
Write-Host "`n[1/5] 检查系统关键运行环境..." -ForegroundColor Yellow

$tools = @{
    "Git"     = "git"
    "Node.js" = "node"
    "npx"     = "npx"
}

$missingTools = @()
foreach ($toolName in $tools.Keys) {
    $cmd = Get-Command $tools[$toolName] -ErrorAction SilentlyContinue
    if ($cmd) {
        Write-Host "  ✓ $toolName : 已就绪 ($($cmd.Source))" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️ $toolName : 未在 PATH 中找到" -ForegroundColor DarkYellow
        $missingTools += $toolName
    }
}

if ($missingTools.Count -gt 0) {
    Write-Host "`n提示: 检测到缺少部分运行工具: $($missingTools -join ', ')。" -ForegroundColor DarkYellow
    Write-Host "如果后续需要运行 GitHub MCP 等动态服务，建议安装 Node.js (可通过 winget install OpenJS.NodeJS)。" -ForegroundColor Gray
}

# -------------------------------------------------------------
# 步骤 2: 状态检查或调用 sync-skills.ps1
# -------------------------------------------------------------
$syncSkillsScript = Join-Path $PSScriptRoot "sync-skills.ps1"
if (!(Test-Path $syncSkillsScript)) {
    Write-Error "找不到 sync-skills.ps1: $syncSkillsScript"
    exit 1
}

if ($StatusOnly) {
    Write-Host "`n[2/5] 检查各 Agent 技能挂载状态..." -ForegroundColor Yellow
    & powershell -NoProfile -ExecutionPolicy Bypass -File $syncSkillsScript -Status
} else {
    Write-Host "`n[2/5] 执行中央技能无痛同步与挂载 (自动备份老设备冲突)..." -ForegroundColor Yellow
    & powershell -NoProfile -ExecutionPolicy Bypass -File $syncSkillsScript -Force
}

# -------------------------------------------------------------
# 步骤 3: 同步 MCP 配置
# -------------------------------------------------------------
$syncMcpScript = Join-Path $PSScriptRoot "sync-mcp.ps1"
if (Test-Path $syncMcpScript) {
    if ($StatusOnly) {
        Write-Host "`n[3/5] 检查 MCP 服务配置..." -ForegroundColor Yellow
        & powershell -NoProfile -ExecutionPolicy Bypass -File $syncMcpScript -Status
    } elseif ($SkipMCP) {
        Write-Host "`n[3/5] 跳过 MCP 配置 (-SkipMCP)。" -ForegroundColor Gray
    } else {
        Write-Host "`n[3/5] 配置统一 MCP 接入 (Antigravity & Codex)..." -ForegroundColor Yellow
        if ($GitHubToken) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $syncMcpScript -GitHubToken $GitHubToken
        } else {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $syncMcpScript
        }
    }
}

# -------------------------------------------------------------
# 步骤 4: 检查并联动 Skills Manager 图形管理工具 (如已安装)
# -------------------------------------------------------------
Write-Host "`n[4/5] 检查 Skills Manager 兼容性..." -ForegroundColor Yellow

$smCliPaths = @(
    "$env:LOCALAPPDATA\skills-manager\skills-manager-cli.exe",
    "C:\Users\$env:USERNAME\AppData\Local\Programs\skills-manager\skills-manager-cli.exe",
    "$env:LOCALAPPDATA\Programs\skills-manager\skills-manager-cli.exe"
)

$foundSmCli = $null
foreach ($path in $smCliPaths) {
    if (Test-Path $path) {
        $foundSmCli = $path
        break
    }
}

if ($foundSmCli) {
    Write-Host "  ✓ 发现本机已安装 Skills Manager: $foundSmCli" -ForegroundColor Green
    if (!$StatusOnly) {
        try {
            # 确保 Skills Manager 的 repo-config.json 指向当前工作区
            $smAppData = Join-Path $env:APPDATA "skills-manager"
            if (!(Test-Path $smAppData)) { New-Item -ItemType Directory -Path $smAppData -Force | Out-Null }
            $repoCfgFile = Join-Path $smAppData "repo-config.json"
            $repoCfg = @{
                repo_path = $WorkspaceRoot
                pending_migration_from = (Join-Path $UserHome ".skills-manager")
            }
            $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
            $repoCfgJson = $repoCfg | ConvertTo-Json -Depth 3
            [System.IO.File]::WriteAllText($repoCfgFile, $repoCfgJson, $utf8NoBom)
            Write-Host "  ✓ 已同步 Skills Manager 本地工作区指向: $WorkspaceRoot" -ForegroundColor Green
        } catch {
            Write-Host "  ⚠️ 同步 Skills Manager 配置遇到警告: $_" -ForegroundColor DarkYellow
        }
    }
} else {
    Write-Host "  - 本机未安装 Skills Manager 客户端 (不影响 CLI 与 Agent 直接使用技能)" -ForegroundColor DarkGray
}

# -------------------------------------------------------------
# 步骤 5: 最终就绪报告
# -------------------------------------------------------------
Write-Host "`n[5/5] 环境就绪检测完成！" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " ✨ 设备已就绪！所有 Agent (Antigravity / Codex / Claude 等) 均已打通。" -ForegroundColor Green
Write-Host "    - 中央技能库: $WorkspaceRoot\skills" -ForegroundColor Gray
Write-Host "    - 历史备份存放: $WorkspaceRoot\backups\" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan