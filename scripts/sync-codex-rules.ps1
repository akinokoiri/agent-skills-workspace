<#
.SYNOPSIS
Deploy the repository's Codex-only rules; preserve nonempty local differences.
.DESCRIPTION
Git pull does not run this script. A conflicting local AGENTS.md must be reviewed
and merged explicitly. No Gemini/Grok files, skills or config.toml are changed.
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [string]$CodexHome
)

$ErrorActionPreference = 'Stop'
try {
    $sourcePath = Join-Path $PSScriptRoot '..\rules\codex\AGENTS.md'
    if (!(Test-Path -LiteralPath $sourcePath -PathType Leaf) -or
        [string]::IsNullOrWhiteSpace([IO.File]::ReadAllText($sourcePath))) {
        throw 'Repository Codex rules are missing or empty.'
    }
    if (!$CodexHome) {
        $CodexHome = if ($env:CODEX_HOME) { $env:CODEX_HOME } else {
            Join-Path ([Environment]::GetFolderPath('UserProfile')) '.codex'
        }
    }
    if (![IO.Path]::IsPathRooted($CodexHome)) { throw 'CodexHome must be absolute.' }
    $targetPath = Join-Path $CodexHome 'AGENTS.md'
    $target = Get-Item -LiteralPath $targetPath -Force -ErrorAction SilentlyContinue
    if ($target) {
        if ($target.PSIsContainer -or ($target.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw 'Preserved non-regular target; review the local rules path manually.'
        }
        if ([Convert]::ToBase64String([IO.File]::ReadAllBytes($sourcePath)) -ceq
            [Convert]::ToBase64String([IO.File]::ReadAllBytes($targetPath))) {
            Write-Output "ALREADY_CURRENT: $targetPath"
            exit 0
        }
        if ($target.Length -gt 0) {
            Write-Warning "CONFLICT_PRESERVED: compare and merge $sourcePath with $targetPath"
            exit 2
        }
    }
    if ($DryRun) {
        Write-Output "DRY_RUN: would copy Codex rules to $targetPath"
        exit 0
    }
    New-Item -ItemType Directory -Path $CodexHome -Force | Out-Null
    Copy-Item -LiteralPath $sourcePath -Destination $targetPath
    Write-Output "COPIED: $targetPath (reload instructions in a new Codex session)"
} catch {
    Write-Error $_ -ErrorAction Continue
    exit 1
}
