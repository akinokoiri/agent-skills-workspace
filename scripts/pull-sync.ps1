<#
.SYNOPSIS
    Update a clean main checkout by fast-forward; optionally refresh local links.
.DESCRIPTION
    Refuses tracked or untracked changes and never creates/pops a stash. A failed
    Git or sync command stops the workflow. Skills Manager is not invoked.
.PARAMETER NoSync
    Compatibility switch for the default code-only update. Cannot combine with Sync.
.PARAMETER Sync
    Explicitly refresh links on a device managed by sync-skills.ps1. Omit on
    devices whose links are managed by Skills Manager.
.PARAMETER Status
    Read local Git and link status only. Does not fetch, pull, stash or mount.
#>
[CmdletBinding()]
param([switch]$NoSync, [switch]$Sync, [switch]$Status)
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Workflow.Common.psm1') -Force -DisableNameChecking
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path

try {
    if ($Sync -and $NoSync) { throw '-Sync and -NoSync cannot be combined.' }
    $git = Get-WorkflowGit
    if ($Status) {
        $state = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('--no-optional-locks', 'status', '--short', '--branch')
        $state.Output | Write-Output
        if (-not $NoSync) { Invoke-WorkflowSync -Root $workspaceRoot -Status }
        Write-Output 'STATUS_COMPLETE: local observations only; remote freshness was not checked.'
        exit 0
    }
    Assert-CleanWorkflowRepository -Git $git -Root $workspaceRoot
    $pull = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('pull', '--ff-only', 'origin', 'main')
    $pull.Output | Write-Output
    if ($Sync) { Invoke-WorkflowSync -Root $workspaceRoot }
    if ($Sync) { Write-Output 'UPDATE_COMPLETE: main updated and local link synchronization completed.' }
    else { Write-Output 'UPDATE_COMPLETE: main updated; local link synchronization was skipped.' }
    exit 0
} catch {
    Write-Error (Protect-WorkflowOutput ([string]$_))
    exit 1
}
