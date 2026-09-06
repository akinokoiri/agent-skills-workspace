<#
.SYNOPSIS
    零 Token 损耗、防错的技能导入与上载工具 (Skill Ingestion & Sync Tool)
.DESCRIPTION
    面向人类与 AI Agent 的高可靠技能收纳工具：
      1. 本地/跨机执行毫秒级文件系统流转（禁止 LLM 上下文搬运大文件，极大节省 Token）
      2. 严格的 SKILL.md 结构与 YAML Frontmatter 格式验证（防损坏/防残缺）
      3. 技能重名防冲撞检测与带时间戳安全备份（防意外覆盖）
      4. (可选) 自动提交并推送至 GitHub 中央库（一键完成跨机分发闭环）
      5. (可选) 自动更新本机所有 Agent 的 NTFS Junction 挂载
.PARAMETER SourcePath
    本地已有技能的目录路径（例如其他 Agent 的某个技能文件夹，或临时下载的目录）。
.PARAMETER GitUrl
    外部 Git 仓库地址（支持直接拉取远程单一技能仓库）。
.PARAMETER Name
    自定义技能名称（必须符合 kebab-case 规范，如 my-skill）。默认取 SKILL.md 中的 name。
.PARAMETER Force
    若目标已存在同名技能，强制备份并替换。
.PARAMETER Push
    导入成功后，自动执行 git pull --rebase、commit 并 push 到远程 GitHub 仓库。
.PARAMETER NoSync
    导入后跳过运行 sync-skills.ps1 挂载步骤。
.EXAMPLE
    .\scripts\import-skill.ps1 -SourcePath "C:\Users\username\.claude\skills\new-tool" -Push
.EXAMPLE
    .\scripts\import-skill.ps1 -SourcePath "D:\downloads\cool-skill" -Force
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $false)]
    [string]$SourcePath,

    [Parameter(Mandatory = $false)]
    [string]$GitUrl,

    [Parameter(Mandatory = $false)]
    [string]$Name,

    [switch]$Force,
    [switch]$Push,
    [switch]$NoSync
)

$ErrorActionPreference = "Stop"

$WorkspaceRoot = (Resolve-Path "$PSScriptRoot\..").Path
$CentralSkillsDir = Join-Path $WorkspaceRoot "skills"
$BackupsBaseDir = Join-Path $WorkspaceRoot "backups"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " 📦 Skill 快速安全收纳工具 (Zero-Token & Anti-Error)" -ForegroundColor Cyan
Write-Host " 中央技能库: $CentralSkillsDir" -ForegroundColor Gray
Write-Host "============================================================" -ForegroundColor Cyan

# 1. 来源解析与获取
$TempCloneDir = $null
$ResolvedSourceDir = $null

try {
    if ($GitUrl) {
        Write-Host "`n[1/5] 从远程 Git 仓库拉取技能: $GitUrl ..." -ForegroundColor Yellow
        $TempCloneDir = Join-Path $env:TEMP "skill-clone-$([System.Guid]::NewGuid().ToString('N'))"
        git clone --depth 1 $GitUrl $TempCloneDir | Out-Null
        $ResolvedSourceDir = $TempCloneDir
        Write-Host "  ✓ 远程仓库拉取完成。" -ForegroundColor Green
    } elseif ($SourcePath) {
        Write-Host "`n[1/5] 检查本地源路径: $SourcePath ..." -ForegroundColor Yellow
        if (!(Test-Path $SourcePath)) {
            Write-Error "指定的源路径不存在: $SourcePath"
            exit 1
        }
        $ResolvedSourceDir = (Resolve-Path $SourcePath).Path
        Write-Host "  ✓ 本地源路径已确认: $ResolvedSourceDir" -ForegroundColor Green
    } else {
        Write-Error "必须提供 -SourcePath 或 -GitUrl 参数！"
        exit 1
    }

    # 2. 格式与元数据深度合规校验 (死门关卡)
    Write-Host "`n[2/5] 验证技能规范合规性 (SKILL.md & YAML Frontmatter)..." -ForegroundColor Yellow

    $SkillMdPath = Join-Path $ResolvedSourceDir "SKILL.md"
    if (!(Test-Path $SkillMdPath)) {
        Write-Error "合规校验失败: 目标目录下缺少核心定义文件 [SKILL.md]！`n路径: $ResolvedSourceDir"
        exit 1
    }

    $skillContent = Get-Content -Path $SkillMdPath -Raw -Encoding UTF8
    if ($skillContent -notmatch "(?s)^---\s*\r?\n(.*?)\r?\n---") {
        Write-Error "合规校验失败: [SKILL.md] 头部缺少标准 YAML Frontmatter (以 '---' 开头与结尾)！"
        exit 1
    }

    $frontmatter = $matches[1]

    # 提取 name
    $declaredName = $null
    if ($frontmatter -match "(?m)^name:\s*['""]?([a-zA-Z0-9_-]+)['""]?\s*$") {
        $declaredName = $matches[1].Trim().ToLower()
    }

    # 提取 description
    $declaredDesc = $null
    if ($frontmatter -match "(?m)^description:\s*(.+)$") {
        $declaredDesc = $matches[1].Trim()
    }

    if ([string]::IsNullOrWhiteSpace($declaredName)) {
        Write-Error "合规校验失败: YAML Frontmatter 中缺少或未定义有效的 [name] 字段！"
        exit 1
    }

    if ([string]::IsNullOrWhiteSpace($declaredDesc)) {
        Write-Error "合规校验失败: YAML Frontmatter 中缺少或未定义有效的 [description] 字段！"
        exit 1
    }

    # 确定最终技能目录名
    $TargetSkillName = if ($Name) { $Name.ToLower() } else { $declaredName }

    # 校验命名是否符合 kebab-case
    if ($TargetSkillName -notmatch "^[a-z0-9]+(-[a-z0-9]+)*$") {
        Write-Error "合规校验失败: 技能名称 [$TargetSkillName] 不符合规范！必须仅包含小写字母、数字及连字符 (例如: my-great-skill)。"
        exit 1
    }

    Write-Host "  ✓ 技能名称: $TargetSkillName" -ForegroundColor Green
    Write-Host "  ✓ 技能描述: $declaredDesc" -ForegroundColor Gray

    # 3. 冲突侦测与安全写入
    Write-Host "`n[3/5] 检测命名冲突与数据安全..." -ForegroundColor Yellow
    $DestPath = Join-Path $CentralSkillsDir $TargetSkillName

    if (Test-Path $DestPath) {
        Write-Host "  ⚠️ 中央库中已存在同名技能: $TargetSkillName" -ForegroundColor DarkYellow
        if (!$Force) {
            Write-Error "操作中止: 目标技能 [$TargetSkillName] 已存在！`n如需覆盖已有版本，请附带 -Force 参数（脚本将自动对旧版本创建时间戳备份）。"
            exit 1
        }

        # 执行安全备份
        $backupTimestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $backupTarget = Join-Path (Join-Path $BackupsBaseDir $backupTimestamp) $TargetSkillName
        if (!(Test-Path (Split-Path $backupTarget -Parent))) {
            New-Item -ItemType Directory -Path (Split-Path $backupTarget -Parent) -Force | Out-Null
        }
        Copy-Item -Path $DestPath -Destination $backupTarget -Recurse -Force
        Write-Host "  ✓ 已对原版本创建安全备份: $backupTarget" -ForegroundColor Green

        Remove-Item -Path $DestPath -Recurse -Force
    }

    # 执行拷贝 (排除 .git 等冗余元数据)
    New-Item -ItemType Directory -Path $DestPath -Force | Out-Null
    Get-ChildItem -Path $ResolvedSourceDir -Force | Where-Object { $_.Name -ne ".git" } | ForEach-Object {
        Copy-Item -Path $_.FullName -Destination $DestPath -Recurse -Force
    }
    Write-Host "  ✓ 技能已成功安全收纳至: $DestPath" -ForegroundColor Green

    # 4. 本地各 Agent Junction 挂载
    if (!$NoSync) {
        Write-Host "`n[4/5] 刷新本地各 Agent 技能挂载 (sync-skills.ps1)..." -ForegroundColor Yellow
        $syncScript = Join-Path $WorkspaceRoot "scripts\sync-skills.ps1"
        if (Test-Path $syncScript) {
            & $syncScript
        }
    } else {
        Write-Host "`n[4/5] 跳过本地挂载刷新 (-NoSync)" -ForegroundColor Gray
    }

    # 5. Git 云端推送闭环
    if ($Push) {
        Write-Host "`n[5/5] 执行 Git 提交与远程同步..." -ForegroundColor Yellow
        Push-Location $WorkspaceRoot
        try {
            # 先安全拉取远端更新
            Write-Host "  正在同步远端最新状态 (git pull --rebase)..." -ForegroundColor Gray
            git pull --rebase origin main

            # 添加并提交新技能
            git add "skills/$TargetSkillName"
            $commitMsg = "feat(skill): add/update $TargetSkillName"
            git commit -m $commitMsg
            Write-Host "  ✓ 已提交更改: $commitMsg" -ForegroundColor Green

            # 推送到 GitHub
            Write-Host "  正在推送到 GitHub 远程仓库..." -ForegroundColor Gray
            git push origin main
            Write-Host "  ✓ 远程推送成功！其他机器现已可随时同步。" -ForegroundColor Green
        } finally {
            Pop-Location
        }
    } else {
        Write-Host "`n[5/5] 未指定 -Push，修改仅保存在本地工作区。" -ForegroundColor Gray
        Write-Host "      后续可在终端运行: git add skills/$TargetSkillName; git commit -m 'feat: add $TargetSkillName'; git push" -ForegroundColor DarkGray
    }

    Write-Host "`n============================================================" -ForegroundColor Cyan
    Write-Host " 🎉 技能 [$TargetSkillName] 处理完毕！" -ForegroundColor Green
    Write-Host "============================================================" -ForegroundColor Cyan

} finally {
    # 清理临时克隆目录
    if ($TempCloneDir -and (Test-Path $TempCloneDir)) {
        Remove-Item -Path $TempCloneDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
