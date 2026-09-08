<#
.SYNOPSIS
    Configure this device's skill entrances from the current checkout.
.DESCRIPTION
    Calls sync-skills only. Skills Manager and MCP have separate configuration
    and are never initialized, migrated, or synchronized by this wrapper.
.PARAMETER StatusOnly
    Report current entrances without writing.
.PARAMETER DryRun
    Preview sync-skills actions without writing.
.PARAMETER Force
    Explicitly permit sync-skills to replace conflicts after backing them up.
.PARAMETER SkipMCP
    Legacy compatibility switch. MCP is always outside this setup workflow.
.PARAMETER GitHubToken
    Legacy parameter: rejected. Configure MCP separately on the local device.
#>
[CmdletBinding()]
param(
    [switch]$StatusOnly,
    [switch]$DryRun,
    [switch]$Force,
    [string]$UserProfilePath,
    [switch]$SkipMCP,
    [string]$GitHubToken
)
$ErrorActionPreference = 'Stop'
if ($GitHubToken) { throw 'MCP is configured separately; setup-device does not accept a token.' }
if ($StatusOnly -and ($DryRun -or $Force)) { throw 'StatusOnly cannot be combined with DryRun or Force.' }
$syncScript = Join-Path $PSScriptRoot 'sync-skills.ps1'
if (-not (Test-Path -LiteralPath $syncScript -PathType Leaf)) { throw 'sync-skills.ps1 is missing from this checkout.' }
$powershellPath = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
$childArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $syncScript)
if ($StatusOnly) { $childArgs += '-Status' }
if ($DryRun) { $childArgs += '-DryRun' }
if ($Force) { $childArgs += '-Force' }
if ($UserProfilePath) { $childArgs += @('-UserProfilePath', $UserProfilePath) }
& $powershellPath @childArgs
$syncExit = $LASTEXITCODE
if ($syncExit -ne 0) {
    Write-Error ('Skill entrance check/update did not complete (exit ' + $syncExit + '). Existing conflicts require review.') -ErrorAction Continue
    exit $syncExit
}
if ($StatusOnly) { Write-Output 'SETUP_STATUS_COMPLETE: see the reported entrance states.' }
elseif ($DryRun) { Write-Output 'SETUP_PREVIEW_COMPLETE: no setup changes requested.' }
else { Write-Output 'SETUP_SYNC_COMPLETE: see individual updated and preserved entries above.' }
Write-Output 'Skills Manager presets, MCP credentials, and other devices were not changed by setup-device.'
