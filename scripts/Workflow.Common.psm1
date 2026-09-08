Set-StrictMode -Version 2.0

function Protect-WorkflowOutput {
    param([AllowEmptyString()][string]$Text)
    $safe = [regex]::Replace($Text, '(?i)(https?://)[^/\s@]+@', '$1[REDACTED]@')
    $safe = [regex]::Replace($safe, '(?i)([?&](?:access_token|token|auth|key)=)[^&\s]+', '$1[REDACTED]')
    $safe = [regex]::Replace($safe, '(?i)(authorization:\s*(?:basic|bearer)\s+)\S+', '$1[REDACTED]')
    return [regex]::Replace($safe, '(?:github_pat_[A-Za-z0-9_]+|gh[pousr]_[A-Za-z0-9_]+)', '[REDACTED]')
}

function Invoke-WorkflowNative {
    param(
        [Parameter(Mandatory=$true)][string]$Executable,
        [string[]]$ArgumentList = @(),
        [int[]]$AllowedExitCodes = @(0),
        [string]$Label = 'Command'
    )
    # PS 5.1 can turn native stderr into ErrorRecord even on success. Capture both
    # streams, then use the native exit code and expose only sanitized output.
    $resolvedExecutable = (Get-Command $Executable -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
    $previousPreference = $ErrorActionPreference
    try {
        $ErrorActionPreference = 'Continue'
        $global:LASTEXITCODE = $null
        $output = @(& $resolvedExecutable @ArgumentList 2>&1)
        $code = $global:LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    $safeOutput = @($output | ForEach-Object { Protect-WorkflowOutput ([string]$_) })
    if ($code -notin $AllowedExitCodes) {
        throw ("{0} failed (exit {1}). {2}" -f $Label, $code, ($safeOutput -join [Environment]::NewLine))
    }
    return [pscustomobject]@{ ExitCode = $code; Output = $safeOutput }
}

function Get-WorkflowGit {
    return (Get-Command git -CommandType Application -ErrorAction Stop | Select-Object -First 1).Source
}

function Invoke-WorkflowGit {
    param([string]$Git, [string]$Root, [string[]]$ArgumentList, [int[]]$AllowedExitCodes = @(0))
    return Invoke-WorkflowNative -Executable $Git -ArgumentList (@('-C', $Root) + $ArgumentList) -AllowedExitCodes $AllowedExitCodes -Label ('git ' + $ArgumentList[0])
}

function Assert-CleanWorkflowRepository {
    param([string]$Git, [string]$Root)
    $branch = Invoke-WorkflowGit -Git $Git -Root $Root -ArgumentList @('symbolic-ref', '--quiet', '--short', 'HEAD')
    if (($branch.Output -join '').Trim() -ne 'main') { throw 'Check out main before updating or publishing this repository.' }
    $upstream = Invoke-WorkflowGit -Git $Git -Root $Root -ArgumentList @('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{upstream}')
    if (($upstream.Output -join '').Trim() -ne 'origin/main') { throw 'main must track origin/main before updating or publishing.' }
    $state = Invoke-WorkflowGit -Git $Git -Root $Root -ArgumentList @('status', '--porcelain=v1', '--untracked-files=all')
    if ($state.Output.Count -gt 0) {
        throw 'Working tree is not clean. Commit or resolve local changes before updating/publishing; nothing was stashed or restored.'
    }
}

function Invoke-WorkflowSync {
    param([string]$Root, [switch]$Status)
    $scriptPath = Join-Path $Root 'scripts\sync-skills.ps1'
    if (-not (Test-Path -LiteralPath $scriptPath -PathType Leaf)) { throw "Sync script is missing: $scriptPath" }
    $hostExecutable = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $arguments = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $scriptPath)
    if ($Status) { $arguments += '-Status' }
    $result = Invoke-WorkflowNative -Executable $hostExecutable -ArgumentList $arguments -Label 'Local skill synchronization'
    $result.Output | Write-Output
}

Export-ModuleMember -Function Protect-WorkflowOutput, Invoke-WorkflowNative, Get-WorkflowGit, Invoke-WorkflowGit, Assert-CleanWorkflowRepository, Invoke-WorkflowSync
