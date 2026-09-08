<#
.SYNOPSIS
    Validate and import one skill; optionally publish it or refresh local links.
.DESCRIPTION
    Imports are local unless -Push is explicitly supplied. Publishing requires a
    clean main checkout and fast-forwards before changing the skill. Existing
    contents are retained in backups when -Force is used. No stash or other
    skill manager is used. Failed Git/validation/sync commands stop the workflow.
.PARAMETER Name
    Optional assertion of the exact YAML name; this does not rename metadata.
.PARAMETER NoSync
    Compatibility switch for the default without link synchronization.
.PARAMETER Sync
    Explicitly refresh links on a device managed by sync-skills.ps1. Omit on
    devices whose links are managed by Skills Manager. Cannot combine with NoSync.
.PARAMETER PythonExecutable
    Python executable with PyYAML installed; defaults to python on PATH.
#>
[CmdletBinding()]
param(
    [string]$SourcePath,
    [string]$GitUrl,
    [string]$Name,
    [switch]$Force,
    [switch]$Push,
    [switch]$NoSync,
    [switch]$Sync,
    [string]$PythonExecutable
)
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'Workflow.Common.psm1') -Force -DisableNameChecking
$workspaceRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
$skillsRoot = Join-Path $workspaceRoot 'skills'
$backupsRoot = Join-Path $workspaceRoot 'backups'
$validator = Join-Path $PSScriptRoot 'validate-skills.py'
$installed = $false
$published = $false
$previousPath = $null
$cloneRoot = $null

function Assert-PlainDirectory {
    param([string]$Path)
    $item = Get-Item -LiteralPath $Path -Force
    if (-not $item.PSIsContainer -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
        throw "Expected an ordinary directory: $Path"
    }
}

function Assert-ChildPath {
    param([string]$Path, [string]$Parent)
    $fullPath = [IO.Path]::GetFullPath($Path)
    $prefix = [IO.Path]::GetFullPath($Parent).TrimEnd('\', '/') + [IO.Path]::DirectorySeparatorChar
    if (-not $fullPath.StartsWith($prefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Path is outside its intended directory: $fullPath"
    }
}

function Copy-ImportTree {
    param([string]$Source, [string]$Destination)
    # Copy before replacing the destination, including when importing from a
    # global junction that already points to this skill. Never follow child links.
    New-Item -ItemType Directory -Path $Destination -ErrorAction Stop | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
        if ($item.Name -eq '.git') { continue }
        if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {
            throw "Linked content cannot be imported automatically: $($item.FullName)"
        }
        $target = Join-Path $Destination $item.Name
        if ($item.PSIsContainer) { Copy-ImportTree -Source $item.FullName -Destination $target }
        else { Copy-Item -LiteralPath $item.FullName -Destination $target -ErrorAction Stop }
    }
}

try {
    if ($Sync -and $NoSync) { throw '-Sync and -NoSync cannot be combined.' }
    if ([bool]$SourcePath -eq [bool]$GitUrl) { throw 'Supply exactly one of -SourcePath or -GitUrl.' }
    $git = $null
    if ($GitUrl -or $Push) { $git = Get-WorkflowGit }
    if ($Push) { Assert-CleanWorkflowRepository -Git $git -Root $workspaceRoot }
    if (-not $PythonExecutable) {
        $PythonExecutable = (Get-Command python -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    }
    if (-not (Test-Path -LiteralPath $validator -PathType Leaf)) { throw "Validator is missing: $validator" }
    Assert-PlainDirectory -Path $skillsRoot
    if (-not (Test-Path -LiteralPath $backupsRoot)) { New-Item -ItemType Directory -Path $backupsRoot | Out-Null }
    Assert-PlainDirectory -Path $backupsRoot

    if ($GitUrl) {
        $cloneRoot = Join-Path ([IO.Path]::GetTempPath()) ('skill-clone-' + [guid]::NewGuid().ToString('N'))
        $clone = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('clone', '--depth', '1', '--', $GitUrl, $cloneRoot)
        $clone.Output | Write-Output
        $SourcePath = $cloneRoot
    }
    if (-not (Test-Path -LiteralPath $SourcePath -PathType Container)) { throw 'SourcePath must be a directory containing SKILL.md.' }
    $SourcePath = (Resolve-Path -LiteralPath $SourcePath).Path
    $metadataResult = Invoke-WorkflowNative -Executable $PythonExecutable -ArgumentList @($validator, '--skill-dir', $SourcePath, '--source', '--json') -Label 'Skill metadata validation'
    $metadata = ($metadataResult.Output -join [Environment]::NewLine) | ConvertFrom-Json
    $skillName = [string]$metadata.name
    if ($Name -and $Name -cne $skillName) { throw '-Name must exactly match the declared YAML name; edit the source metadata to rename a skill.' }
    $destination = Join-Path $skillsRoot $skillName
    Assert-ChildPath -Path $destination -Parent $skillsRoot
    if (Test-Path -LiteralPath $destination) {
        Assert-PlainDirectory -Path $destination
        if (-not $Force) { throw "Skill already exists; review it and use -Force to retain a backup and replace it: $skillName" }
    }

    $operationRoot = Join-Path $backupsRoot ('import-' + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N'))
    New-Item -ItemType Directory -Path $operationRoot | Out-Null
    $incomingRoot = Join-Path $operationRoot 'incoming'
    New-Item -ItemType Directory -Path $incomingRoot | Out-Null
    $incoming = Join-Path $incomingRoot $skillName
    Copy-ImportTree -Source $SourcePath -Destination $incoming
    $validated = Invoke-WorkflowNative -Executable $PythonExecutable -ArgumentList @($validator, '--skill-dir', $incoming, '--expected-name', $skillName) -Label 'Copied skill validation'
    $validated.Output | Write-Output

    if ($Push) {
        # Check again after staging the input. A rejected/failed pull leaves the
        # tracked skill untouched. Backups are ignored by this repository.
        Assert-CleanWorkflowRepository -Git $git -Root $workspaceRoot
        $pull = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('pull', '--ff-only', 'origin', 'main')
        $pull.Output | Write-Output
        Assert-CleanWorkflowRepository -Git $git -Root $workspaceRoot
        $localHead = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('rev-parse', 'HEAD')
        $remoteHead = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('rev-parse', 'refs/remotes/origin/main')
        if (($localHead.Output -join '') -ne ($remoteHead.Output -join '')) {
            throw 'main contains unpublished commits. Publish or resolve them separately before using import -Push.'
        }
    }
    Assert-PlainDirectory -Path $skillsRoot
    Assert-PlainDirectory -Path $backupsRoot
    Assert-PlainDirectory -Path $operationRoot
    if (Test-Path -LiteralPath $destination) {
        Assert-PlainDirectory -Path $destination
        if (-not $Force) { throw "Skill now exists after updating; use -Force after reviewing it: $skillName" }
        $previousPath = Join-Path $operationRoot 'previous'
    }
    $restore = [ordered]@{ target = $destination; previous = $previousPath; name = $skillName }
    [IO.File]::WriteAllText((Join-Path $operationRoot 'restore-manifest.json'), ($restore | ConvertTo-Json), (New-Object Text.UTF8Encoding($false)))
    if ($previousPath) {
        Assert-ChildPath -Path $destination -Parent $skillsRoot
        Assert-ChildPath -Path $previousPath -Parent $operationRoot
        [IO.Directory]::Move($destination, $previousPath)
    }
    try {
        Assert-ChildPath -Path $incoming -Parent $operationRoot
        Assert-ChildPath -Path $destination -Parent $skillsRoot
        # Directory.Move fails if another writer creates the destination; it
        # cannot silently nest the incoming skill inside an existing directory.
        [IO.Directory]::Move($incoming, $destination)
        $installed = $true
    } catch {
        if ($previousPath -and (Test-Path -LiteralPath $previousPath) -and -not (Test-Path -LiteralPath $destination)) {
            Assert-ChildPath -Path $previousPath -Parent $operationRoot
            Assert-ChildPath -Path $destination -Parent $skillsRoot
            [IO.Directory]::Move($previousPath, $destination)
        }
        throw
    }

    if ($Push) {
        $relativeSkill = 'skills/' + $skillName
        $added = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('add', '--', $relativeSkill)
        $changed = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('diff', '--cached', '--quiet', '--', $relativeSkill) -AllowedExitCodes @(0, 1)
        if ($changed.ExitCode -eq 1) {
            $commit = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('commit', '-m', ('Import skill: ' + $skillName), '--', $relativeSkill)
            $commit.Output | Write-Output
        }
        $pushResult = Invoke-WorkflowGit -Git $git -Root $workspaceRoot -ArgumentList @('push', 'origin', 'HEAD:main')
        $pushResult.Output | Write-Output
        $published = $true
        Write-Output 'PUBLISH_COMPLETE: origin/main accepted the imported skill.'
    }
    if ($Sync) { Invoke-WorkflowSync -Root $workspaceRoot }
    Write-Output ("IMPORT_COMPLETE: name={0}; published={1}; links_refreshed={2}" -f $skillName, $published, [bool]$Sync)
    if ($previousPath) { Write-Output "Previous skill retained at: $previousPath" }
    exit 0
} catch {
    if ($installed) { Write-Output "IMPORT_PARTIAL: files were imported, but a later step failed; published=$published. Local files and Git state were retained." }
    if ($previousPath -and (Test-Path -LiteralPath $previousPath)) { Write-Output "Previous skill retained at: $previousPath" }
    Write-Error (Protect-WorkflowOutput ([string]$_))
    exit 1
} finally {
    # Retain the newly allocated clone as an input snapshot. No recursive delete
    # is performed on repository-provided trees, which may contain linked paths.
    if ($cloneRoot -and (Test-Path -LiteralPath $cloneRoot)) { Write-Output "Clone snapshot retained at: $cloneRoot" }
}
