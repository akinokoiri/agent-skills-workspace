<#
.SYNOPSIS
    跨 Agent 与跨设备统一 MCP 服务同步与注入脚本 (Antigravity & Codex)
.DESCRIPTION
    读取仓库 mcp/ 目录下的配置模板或用户提供的 Token，
    将 GitHub 等核心 MCP 服务自动配置到：
      1. Antigravity: ~/.gemini/config/mcp_config.json
      2. Antigravity: ~/.gemini/antigravity/mcp_config.json
      3. ChatGPT / Codex: ~/.codex/config.toml (若存在则合入 mcp_servers)
.PARAMETER GitHubToken
    GitHub Personal Access Token。若未指定，依次从本地 .env、系统环境变量 GITHUB_PERSONAL_ACCESS_TOKEN 或已有配置文件中提取。
.PARAMETER Status
    仅检查当前各 Agent 的 MCP 挂载状态。
#>

[CmdletBinding()]
param(
    [string]$GitHubToken,
    [switch]$Status
)

$ErrorActionPreference = "Stop"

$WorkspaceRoot = (Resolve-Path "$PSScriptRoot\..").Path
$UserHome = [System.Environment]::GetFolderPath("UserProfile")

$GeminiConfigFile = Join-Path $UserHome ".gemini\config\mcp_config.json"
$GeminiAgyFile = Join-Path $UserHome ".gemini\antigravity\mcp_config.json"
$CodexConfigFile = Join-Path $UserHome ".codex\config.toml"
$LocalEnvFile = Join-Path $WorkspaceRoot "mcp\.env"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 🔌 跨 Agent 统一 MCP 同步配置工具" -ForegroundColor Cyan
Write-Host " 工作区根目录: $WorkspaceRoot" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

# 1. 提取 GitHub Token
$ResolvedToken = $GitHubToken

if ([string]::IsNullOrWhiteSpace($ResolvedToken) -and (Test-Path $LocalEnvFile)) {
    Get-Content $LocalEnvFile | ForEach-Object {
        $line = $_.Trim()
        if ($line -match '^GITHUB_PERSONAL_ACCESS_TOKEN\s*=\s*(.+)$') {
            $val = $matches[1].Trim().Trim('"').Trim("'")
            if ($val -and $val -ne "your_github_token_here") {
                $ResolvedToken = $val
            }
        }
    }
}

if ([string]::IsNullOrWhiteSpace($ResolvedToken) -and $env:GITHUB_PERSONAL_ACCESS_TOKEN) {
    $ResolvedToken = $env:GITHUB_PERSONAL_ACCESS_TOKEN
}

# 兜底：从已有 Antigravity 配置中尝试重用
if ([string]::IsNullOrWhiteSpace($ResolvedToken)) {
    foreach ($cfgPath in @($GeminiConfigFile, $GeminiAgyFile)) {
        if (Test-Path $cfgPath) {
            try {
                $raw = Get-Content $cfgPath -Raw -ErrorAction SilentlyContinue | ConvertFrom-Json -ErrorAction SilentlyContinue
                if ($raw.mcpServers.github.env.GITHUB_PERSONAL_ACCESS_TOKEN) {
                    $candidate = $raw.mcpServers.github.env.GITHUB_PERSONAL_ACCESS_TOKEN
                    if ($candidate -and $candidate -ne "your_github_token_here") {
                        $ResolvedToken = $candidate
                        break
                    }
                }
            } catch {}
        }
    }
}

# 2. 状态检查模式
if ($Status) {
    Write-Host "`n📊 [检查当前各 Agent MCP 状态]" -ForegroundColor Yellow
    
    # 检查 Antigravity
    Write-Host "`n[Antigravity] -> $GeminiConfigFile" -ForegroundColor White
    if (Test-Path $GeminiConfigFile) {
        try {
            $geminiCfg = Get-Content $GeminiConfigFile -Raw | ConvertFrom-Json
            if ($geminiCfg.mcpServers.github) {
                Write-Host "  ✓ GitHub MCP: 已配置 (command: $($geminiCfg.mcpServers.github.command))" -ForegroundColor Green
            } else {
                Write-Host "  - GitHub MCP: 未配置" -ForegroundColor DarkGray
            }
        } catch {
            Write-Host "  ⚠️ 配置文件解析异常: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  (配置文件不存在)" -ForegroundColor DarkGray
    }

    # 检查 Codex
    Write-Host "`n[Codex] -> $CodexConfigFile" -ForegroundColor White
    if (Test-Path $CodexConfigFile) {
        $codexRaw = Get-Content $CodexConfigFile -Raw
        if ($codexRaw -match '\[mcp_servers\.github\]') {
            Write-Host "  ✓ GitHub MCP: 已配置" -ForegroundColor Green
        } else {
            Write-Host "  - GitHub MCP: 未配置" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "  (配置文件不存在)" -ForegroundColor DarkGray
    }

    Write-Host "`n状态检查完成。" -ForegroundColor Cyan
    exit 0
}

# 3. 执行同步
if ([string]::IsNullOrWhiteSpace($ResolvedToken)) {
    Write-Host "`n⚠️ 未找到有效 GitHub Token (可在命令行传 -GitHubToken，或在 mcp/.env 中配置)" -ForegroundColor Yellow
    Write-Host "   跳过自动写入，如需配置请提供 Token 后再次运行。" -ForegroundColor Gray
    exit 0
}

# 掩码显示 Token
$maskedToken = $ResolvedToken.Substring(0, [Math]::Min(7, $ResolvedToken.Length)) + "..." + $ResolvedToken.Substring([Math]::Max(0, $ResolvedToken.Length - 4))
Write-Host "🔑 使用 GitHub Token: $maskedToken" -ForegroundColor Gray

# A. 写入 Antigravity (~/.gemini/config/mcp_config.json 及 ~/.gemini/antigravity/mcp_config.json)
$antigravityConfigObj = @{
    mcpServers = @{
        github = @{
            command = "npx"
            args = @("-y", "@modelcontextprotocol/server-github")
            env = @{
                GITHUB_PERSONAL_ACCESS_TOKEN = $ResolvedToken
            }
        }
    }
}
$antigravityJson = $antigravityConfigObj | ConvertTo-Json -Depth 5

foreach ($targetFile in @($GeminiConfigFile, $GeminiAgyFile)) {
    $parentDir = Split-Path $targetFile -Parent
    if (!(Test-Path $parentDir)) { New-Item -ItemType Directory -Path $parentDir -Force | Out-Null }
    
    $utf8NoBom = [System.Text.UTF8Encoding]::new($false)
    # 若已有配置且包含其他 server，合并而非覆盖
    if (Test-Path $targetFile) {
        try {
            $existing = Get-Content $targetFile -Raw | ConvertFrom-Json
            if ($existing.mcpServers) {
                # 合入 github
                $existing.mcpServers | Add-Member -MemberType NoteProperty -Name "github" -Value $antigravityConfigObj.mcpServers.github -Force
                $mergedJson = $existing | ConvertTo-Json -Depth 5
                [System.IO.File]::WriteAllText($targetFile, $mergedJson, $utf8NoBom)
                Write-Host "   ✓ 已合并写入 Antigravity MCP: $targetFile" -ForegroundColor Green
                continue
            }
        } catch {}
    }
    [System.IO.File]::WriteAllText($targetFile, $antigravityJson, $utf8NoBom)
    Write-Host "   ✓ 已写入 Antigravity MCP: $targetFile" -ForegroundColor Green
}

# B. 写入 Codex (~/.codex/config.toml)
if (Test-Path (Split-Path $CodexConfigFile -Parent)) {
    $codexGithubToml = @"

[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
startup_timeout_sec = 60

[mcp_servers.github.env]
GITHUB_PERSONAL_ACCESS_TOKEN = "$ResolvedToken"
"@

    if (Test-Path $CodexConfigFile) {
        $codexContent = Get-Content $CodexConfigFile -Raw
        if ($codexContent -match '\[mcp_servers\.github\]') {
            # 已经存在 github 配置，更新 token
            $codexContent = [regex]::Replace(
                $codexContent,
                '(?ms)\[mcp_servers\.github\].*?(?=\n\[|\z)',
                $codexGithubToml.Trim() + "`n"
            )
            [System.IO.File]::WriteAllText($CodexConfigFile, $codexContent, [System.Text.Encoding]::UTF8)
            Write-Host "   ✓ 已更新 Codex MCP 配置中的 GitHub 服务: $CodexConfigFile" -ForegroundColor Green
        } else {
            # 追加到文件尾部
            [System.IO.File]::AppendAllText($CodexConfigFile, "`n" + $codexGithubToml, [System.Text.Encoding]::UTF8)
            Write-Host "   ✓ 已追加 GitHub MCP 服务到 Codex: $CodexConfigFile" -ForegroundColor Green
        }
    } else {
        [System.IO.File]::WriteAllText($CodexConfigFile, $codexGithubToml, [System.Text.Encoding]::UTF8)
        Write-Host "   ✓ 已创建 Codex 基础配置并注入 GitHub MCP: $CodexConfigFile" -ForegroundColor Green
    }
}

Write-Host "`n🎉 MCP 同步完成！" -ForegroundColor Green