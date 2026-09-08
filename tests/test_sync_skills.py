"""Windows offline behavior checks; never invoke a manager, Git, or the real sync entry.

Run with an explicit PowerShell executable and a fresh sandbox parent, for example:
    python tests/test_sync_skills.py --powershell C:/path/to/pwsh.exe --sandbox-root C:/temp/sync-checks
Each fixture copies only sync-skills.ps1, uses UserProfilePath, and clears PATH while
redirecting HOME, USERPROFILE, APPDATA, LOCALAPPDATA, TEMP and PowerShell profiles.
unittest discovery defaults to Windows PowerShell 5.1 and a fresh mkdtemp root;
SYNC_TEST_POWERSHELL and SYNC_TEST_SANDBOX_ROOT can select explicit paths.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPARSE = 0x400
SOURCE = Path(__file__).resolve().parents[1] / "scripts" / "sync-skills.ps1"
POWERSHELL = None
SANDBOX = None
COMMAND_LOG = []
ALLOWED_COMMANDS = {
    "Resolve-Path", "Join-Path", "Test-Path", "Get-Item", "Split-Path",
    "Write-Warning", "Write-Host", "New-Item", "Out-Null", "Get-ChildItem",
    "Where-Object", "Sort-Object", "Get-Date", "Copy-Item", "ConvertTo-Json",
    "Set-Content", "Move-Item", "Get-Content", "ConvertFrom-Json", "Add-Member",
    "Get-FileHash", "Get-NormalPath", "Get-Entry", "Test-Reparse",
    "Get-LinkTarget", "Test-OwnedLink", "Test-SafeDirectory", "Ensure-Directory",
    "Save-FileBackup", "Save-LinkBackup", "Remove-OwnedLink", "Test-PhysicalTree",
    "Mount-Skill", "Report-Conflict",
}
RUNNER_TEXT = """param([string]$UserProfilePath, [switch]$DryRun, [switch]$Status, [switch]$Force)
$ErrorActionPreference = 'Stop'
$env:PSModulePath = $env:SYNC_TEST_MODULE_PATH
$global:LASTEXITCODE = 0
& (Join-Path $PSScriptRoot 'sync-skills.ps1') @PSBoundParameters
exit $LASTEXITCODE
"""


def is_reparse(path):
    return bool(path.lstat().st_file_attributes & REPARSE)


def assert_physical_ancestors(path):
    for ancestor in (path, *path.parents):
        if ancestor.exists() and is_reparse(ancestor):
            raise AssertionError(f"Sandbox ancestor is a link: {ancestor}")


def configure_runtime(powershell=None, sandbox=None):
    global POWERSHELL, SANDBOX
    if os.name != "nt":
        return
    executable = powershell or os.environ.get("SYNC_TEST_POWERSHELL")
    if executable is None:
        executable = Path(os.environ["SystemRoot"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    executable = Path(executable)
    if not executable.is_absolute() or executable.name.lower() not in {"powershell.exe", "pwsh.exe"}:
        raise ValueError("Specify an absolute PowerShell executable; never search PATH")
    POWERSHELL = executable.resolve(strict=True)
    parent = sandbox or os.environ.get("SYNC_TEST_SANDBOX_ROOT")
    if parent is None:
        temporary_parent = Path(tempfile.gettempdir()).absolute()
        assert_physical_ancestors(temporary_parent)
        temporary_parent = temporary_parent.resolve()
        SANDBOX = Path(tempfile.mkdtemp(prefix="sync-skills-discovery-", dir=temporary_parent)).resolve()
    else:
        SANDBOX = Path(parent).absolute()
        if SANDBOX.exists():
            raise ValueError("Use a fresh sandbox root; existing test runs must not be reused")
        assert_physical_ancestors(SANDBOX.parent)
        SANDBOX.mkdir(parents=True)
        SANDBOX = SANDBOX.resolve()


def write_evidence(result=None):
    if SANDBOX is None:
        return
    (SANDBOX / "invocations.json").write_text(json.dumps(COMMAND_LOG, ensure_ascii=False, indent=2), encoding="utf-8")
    summary = {"source_sha256": hashlib.sha256(SOURCE.read_bytes()).hexdigest(), "powershell": str(POWERSHELL), "sandbox": str(SANDBOX), "real_manager_invocations": 0}
    if result is not None:
        summary.update(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors), skipped=len(result.skipped))
    (SANDBOX / "result.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")


def snapshot(path):
    """Capture content, link targets and mtimes without following any reparse point."""
    result = {}

    def visit(item):
        stat = item.lstat()
        rel = str(item.relative_to(path))
        if stat.st_file_attributes & REPARSE:
            result[rel] = ("link", os.readlink(item), stat.st_mtime_ns)
        elif item.is_dir():
            result[rel] = ("dir", stat.st_mtime_ns)
            for child in sorted(item.iterdir()):
                visit(child)
        else:
            result[rel] = ("file", hashlib.sha256(item.read_bytes()).hexdigest(), stat.st_mtime_ns)

    visit(path)
    return result


class Fixture:
    def __init__(self):
        self.base = Path(tempfile.mkdtemp(prefix="sync-only-", dir=SANDBOX))
        assert_physical_ancestors(self.base)
        # Windows TEMP may use an 8.3 alias; match PowerShell's canonical paths.
        self.base = self.base.resolve()
        self.repo = self.base / "repo"
        self.user = self.base / "user"
        self.outside = self.base / "outside"
        for path in (self.repo / "scripts", self.repo / "skills", self.repo / "rules", self.user, self.outside):
            path.mkdir(parents=True, exist_ok=True)
        self.script = self.repo / "scripts" / "sync-skills.ps1"
        shutil.copyfile(SOURCE, self.script)
        self.runner = self.repo / "scripts" / "run-sync.ps1"
        self.runner.write_text(RUNNER_TEXT, encoding="utf-8-sig")
        self.rule = self.repo / "rules" / "AGENTS.md"
        self.rule.write_text("Shared rule\n", encoding="utf-8")
        self.skill("alpha")
        self.skill("progress-brief")
        self.env = dict(os.environ)
        self.env["PATH"] = ""
        for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "CODEX_HOME", "DOTNET_CLI_HOME", "PSMODULEPATH", "XDG_CONFIG_HOME", "XDG_CACHE_HOME"):
            value = self.base / "environment" / key.lower()
            value.mkdir(parents=True, exist_ok=True)
            self.env[key] = str(value)
        self.env["HOMEDRIVE"], self.env["HOMEPATH"] = os.path.splitdrive(self.env["USERPROFILE"])
        # Only trusted modules shipped beside the explicitly selected PowerShell are available.
        # Windows PS5.1 implements Get-FileHash in its Utility module, not the core snap-in.
        self.module_path = self.env["PSMODULEPATH"] + os.pathsep + str(POWERSHELL.parent / "Modules")
        self.env["PSMODULEPATH"] = self.module_path
        self.env["SYNC_TEST_MODULE_PATH"] = self.module_path
        self.env["POWERSHELL_TELEMETRY_OPTOUT"] = "1"
        self.env["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1"
        self.env["SYNC_AUDIT_SCRIPT"] = str(self.script)
        # Strict AST allowlist: no variable command, call operator, dot sourcing, or native command.
        audit = """
        $tokens = $null; $errors = $null
        $ast = [System.Management.Automation.Language.Parser]::ParseFile($env:SYNC_AUDIT_SCRIPT, [ref]$tokens, [ref]$errors)
        if ($errors.Count) { throw ($errors | Out-String) }
        $commands = @($ast.FindAll({ param($n) $n -is [System.Management.Automation.Language.CommandAst] }, $true) | ForEach-Object {
            [pscustomobject]@{ name=$_.GetCommandName(); invocation=[string]$_.InvocationOperator }
        })
        ConvertTo-Json -InputObject @{ commands=$commands; module_path=$env:PSModulePath; home=$env:HOME; userprofile=$env:USERPROFILE; appdata=$env:APPDATA; localappdata=$env:LOCALAPPDATA; path=$env:PATH } -Compress
        """
        result = self.invoke(["-Command", audit], kind="static-ast")
        if result.returncode:
            raise AssertionError(result.stdout + result.stderr)
        actual = json.loads(result.stdout)
        for key in ("home", "userprofile", "appdata", "localappdata"):
            assert Path(actual[key]).is_relative_to(self.base), actual
        assert actual["path"] in (None, ""), actual["path"]
        allowed_module_paths = {os.path.normcase(str(self.base / "environment/psmodulepath")), os.path.normcase(str(POWERSHELL.parent / "Modules"))}
        for module_path in actual["module_path"].split(os.pathsep):
            assert os.path.normcase(module_path.rstrip("\\/")) in allowed_module_paths, actual["module_path"]
        commands = actual["commands"]
        for command in commands:
            if command["name"] not in ALLOWED_COMMANDS or command["invocation"] != "Unknown":
                raise AssertionError(f"Unreviewed execution path: {command}")
        for denied in ("System.Diagnostics.Process", "Invoke-Expression", "Start-Process", "Add-Type", "Invoke-Command"):
            if denied.lower() in self.script.read_text(encoding="utf-8-sig").lower():
                raise AssertionError(f"Unreviewed native/remote execution path: {denied}")

    def invoke(self, args, kind):
        assert_physical_ancestors(self.base)
        assert self.script.read_bytes() == SOURCE.read_bytes(), "Only an exact source copy may run"
        assert self.runner.read_text(encoding="utf-8-sig") == RUNNER_TEXT, "Only the fixed local runner may invoke the copy"
        assert self.env["PATH"] == ""
        for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP", "CODEX_HOME"):
            assert Path(self.env[key]).is_relative_to(self.base)
        assert self.env["PSMODULEPATH"] == self.module_path
        assert len({key.upper() for key in self.env}) == len(self.env), "Windows environment keys must be unique ignoring case"
        # Windows PS5.1 appends Program Files modules on startup. Reset inside the
        # process before any module-based command, rather than trusting inherited paths.
        if args[0] == "-File":
            assert args[1] == str(self.script)
            args = ["-File", str(self.runner), *args[2:]]
        elif args[0] == "-Command":
            args = ["-Command", "$env:PSModulePath = $env:SYNC_TEST_MODULE_PATH\n" + args[1]]
        else:
            raise AssertionError("Only the fixed local runner or reviewed diagnostic code may run")
        command = [str(POWERSHELL), "-NoLogo", "-NoProfile", "-NonInteractive", *args]
        result = subprocess.run(command, cwd=self.repo, env=self.env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=40)
        COMMAND_LOG.append({"kind": kind, "cwd": str(self.repo), "command": command, "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr})
        return result

    def run(self, *args, expected=0):
        result = self.invoke(["-File", str(self.script), "-UserProfilePath", str(self.user), *args], kind="sync-copy")
        if result.returncode != expected:
            raise AssertionError(f"Expected exit {expected}, got {result.returncode}\n" + result.stdout + result.stderr)
        return result

    def skill(self, name):
        path = self.repo / "skills" / name
        path.mkdir()
        (path / "SKILL.md").write_text(f"---\nname: {name}\ndescription: Fixture.\n---\n", encoding="utf-8")
        return path

    def physical(self, relative, content="keep me"):
        path = self.user / relative
        path.mkdir(parents=True, exist_ok=True)
        (path / "sentinel.txt").write_text(content, encoding="utf-8")
        return path

    def junction(self, path, target):
        assert path.is_relative_to(self.base) and target.is_relative_to(self.base)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.env["SYNC_TEST_LINK"] = str(path)
        self.env["SYNC_TEST_TARGET"] = str(target)
        result = self.invoke(["-Command", "New-Item -ItemType Junction -Path $env:SYNC_TEST_LINK -Target $env:SYNC_TEST_TARGET | Out-Null"], kind="fixture-junction")
        if result.returncode != 0:
            raise AssertionError(result.stdout + result.stderr)

    def watched(self):
        return {str(path): snapshot(path) for path in (self.repo, self.user, self.outside)}


@unittest.skipUnless(os.name == "nt", "These junction behavior checks require Windows")
class SyncBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if POWERSHELL is None or SANDBOX is None:
            configure_runtime()

    @classmethod
    def tearDownClass(cls):
        write_evidence()

    def setUp(self):
        self.f = Fixture()

    def test_dry_run_zero_writes_even_force(self):
        f = self.f
        f.physical(".codex/skills/alpha")
        index = f.user / ".gemini/config/skills.json"
        index.parent.mkdir(parents=True)
        index.write_text('{"entries":[],"custom":42}', encoding="utf-8")
        rule = f.user / ".gemini/config/rules/AGENTS.md"
        rule.parent.mkdir()
        rule.write_text("Customized rule", encoding="utf-8")
        before = f.watched()
        f.run("-DryRun", "-Force")
        self.assertEqual(before, f.watched())

    def test_status_read_only_and_wrong_target_not_healthy(self):
        f = self.f
        f.junction(f.user / ".codex/skills/alpha", f.outside)
        before = f.watched()
        result = f.run("-Status", "-Force")
        self.assertEqual(before, f.watched())
        codex = result.stdout.split("[ChatGPT (Codex)]")[1].split("[Claude Code]")[0]
        self.assertIn("[冲突/非中央联接] alpha", codex)
        self.assertNotIn("[正常联接] alpha", codex)

    def test_default_preserves_physical_unknown_broken_and_old_link(self):
        f = self.f
        physical = f.physical(".codex/skills/alpha")
        old = f.physical(".codex/skills/legacy.old-link")
        unknown = f.user / ".claude/skills/alpha"
        f.junction(unknown, f.outside)
        broken_target = f.base / "removed-target"
        broken_target.mkdir()
        broken = f.user / ".codex/skills/unknown"
        f.junction(broken, broken_target)
        broken_target.rmdir()
        before = {str(p): snapshot(p) for p in (physical, old, unknown, broken)}
        f.run(expected=2)
        self.assertEqual(before, {str(p): snapshot(p) for p in (physical, old, unknown, broken)})
        self.assertFalse((f.repo / "backups").exists())

    def test_force_preserves_foreign_link_and_its_target(self):
        f = self.f
        (f.outside / "sentinel").write_text("external", encoding="utf-8")
        link = f.user / ".codex/skills/alpha"
        f.junction(link, f.outside)
        before = (snapshot(link), snapshot(f.outside))
        f.run("-Force", expected=2)
        self.assertEqual(before, (snapshot(link), snapshot(f.outside)))

    def test_exclusion_removes_only_owned_link_with_restoration_record(self):
        f = self.f
        own = f.user / ".codex/skills/progress-brief"
        f.junction(own, f.repo / "skills/progress-brief")
        foreign = f.user / ".claude/skills/progress-brief"
        f.junction(foreign, f.outside)
        physical = f.physical(".dsh/skills/progress-brief")
        before = (snapshot(foreign), snapshot(physical), snapshot(f.repo / "skills"))
        f.run("-Force")
        self.assertFalse(os.path.lexists(own))
        self.assertEqual(before, (snapshot(foreign), snapshot(physical), snapshot(f.repo / "skills")))
        records = list((f.repo / "backups").rglob("progress-brief.link.json"))
        self.assertEqual(len(records), 1)
        record = json.loads(records[0].read_text(encoding="utf-8-sig"))
        self.assertEqual(record["original"], str(own))

    def test_force_backs_up_physical_skill_before_mounting(self):
        f = self.f
        dest = f.physical(".codex/skills/alpha", "precious content")
        f.run("-Force")
        self.assertTrue(is_reparse(dest))
        backups = list((f.repo / "backups").rglob("sentinel.txt"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "precious content")
        records = list((f.repo / "backups").rglob("alpha.restore.json"))
        self.assertEqual(len(records), 1)
        self.assertEqual(json.loads(records[0].read_text(encoding="utf-8-sig"))["original"], str(dest))

    def test_force_preserves_physical_tree_containing_foreign_link(self):
        f = self.f
        dest = f.physical(".codex/skills/alpha")
        f.junction(dest / "nested", f.outside)
        before = snapshot(dest)
        f.run("-Force", expected=2)
        self.assertEqual(before, snapshot(dest))

    def test_reparse_agent_parent_and_workspace_parent_are_preserved(self):
        f = self.f
        f.junction(f.user / ".codex", f.outside)
        f.junction(f.repo / ".agents", f.outside)
        before = snapshot(f.outside)
        f.run("-Force", expected=2)
        self.assertEqual(before, snapshot(f.outside))
        self.assertFalse((f.outside / "skills").exists())

    def test_config_and_custom_rules_preserved_default_force_merges_and_backs_up(self):
        f = self.f
        index = f.user / ".gemini/config/skills.json"
        index.parent.mkdir(parents=True)
        original = '{"entries":[{"path":"E:/中文技能"}],"custom":{"enabled":true,"标题":"保留中文配置"}}'
        index.write_text(original, encoding="utf-8")
        rule = index.parent / "rules/AGENTS.md"
        rule.parent.mkdir()
        rule.write_text("Customized rule", encoding="utf-8")
        f.run(expected=2)
        self.assertEqual(index.read_text(encoding="utf-8"), original)
        self.assertEqual(rule.read_text(encoding="utf-8"), "Customized rule")
        f.run("-Force")
        merged = json.loads(index.read_text(encoding="utf-8-sig"))
        self.assertTrue(merged["custom"]["enabled"])
        self.assertEqual(merged["custom"]["标题"], "保留中文配置")
        self.assertIn({"path": "E:/中文技能"}, merged["entries"])
        self.assertIn({"path": (f.repo / "skills").as_posix()}, merged["entries"])
        self.assertEqual(rule.read_bytes(), f.rule.read_bytes())
        index_backups = list((f.repo / "backups").rglob("skills.json"))
        self.assertEqual(len(index_backups), 1)
        self.assertEqual(index_backups[0].read_text(encoding="utf-8"), original)
        rule_backups = list((f.repo / "backups").rglob("AGENTS.md"))
        self.assertEqual(len(rule_backups), 1)
        self.assertEqual(rule_backups[0].read_text(encoding="utf-8"), "Customized rule")
        before = f.watched()
        f.run("-Force")
        self.assertEqual(before, f.watched(), "A second sync should be a no-op")

    def test_invalid_index_is_preserved(self):
        f = self.f
        index = f.user / ".gemini/config/skills.json"
        index.parent.mkdir(parents=True)
        index.write_text("{invalid json", encoding="utf-8")
        f.run("-Force", expected=2)
        self.assertEqual(index.read_text(encoding="utf-8"), "{invalid json")

    def test_config_rule_and_workspace_links_preserve_external_data(self):
        f = self.f
        (f.outside / "sentinel").write_text("external", encoding="utf-8")
        links = [f.user / ".gemini/config/skills.json", f.user / ".gemini/config/rules/AGENTS.md", f.repo / ".agents/skills"]
        for link in links:
            f.junction(link, f.outside)
        before = (snapshot(f.outside), [snapshot(p) for p in links])
        f.run("-Force", expected=2)
        self.assertEqual(before, (snapshot(f.outside), [snapshot(p) for p in links]))

    def test_reparse_backup_parent_blocks_move(self):
        f = self.f
        dest = f.physical(".codex/skills/alpha")
        f.junction(f.repo / "backups", f.outside)
        before = (snapshot(dest), snapshot(f.outside))
        result = f.run("-Force", expected=1)
        self.assertIn("备份目录不可用", result.stderr)
        self.assertEqual(before, (snapshot(dest), snapshot(f.outside)))

    def test_relative_user_root_is_rejected_without_writes(self):
        f = self.f
        before = f.watched()
        result = f.invoke(["-File", str(f.script), "-UserProfilePath", "relative-root"], kind="sync-copy-invalid-root")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(before, f.watched())

    def test_absolute_user_root_normalizes_dot_segments(self):
        f = self.f
        user_root = str(f.user / ".." / "user")
        result = f.invoke(["-File", str(f.script), "-UserProfilePath", user_root], kind="sync-copy-normalized-root")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(is_reparse(f.user / ".codex/skills/alpha"))
        self.assertFalse((f.repo / "user").exists())

    def test_owned_relative_symbolic_links_are_recognized_and_safely_excluded(self):
        f = self.f
        normal = f.user / ".codex/skills/alpha"
        excluded = f.user / ".codex/skills/progress-brief"
        normal.parent.mkdir(parents=True)
        try:
            for link in (normal, excluded):
                target = f.repo / "skills" / link.name
                relative = os.path.relpath(target, link.parent)
                self.assertTrue((link.parent / relative).resolve().is_relative_to(f.base))
                os.symlink(relative, link, target_is_directory=True)
        except OSError as exc:
            if getattr(exc, "winerror", None) == 1314:
                self.skipTest("Windows does not allow unprivileged symbolic-link creation on this host")
            raise
        before = (snapshot(normal), snapshot(f.repo / "skills"))
        f.run()
        self.assertEqual(before, (snapshot(normal), snapshot(f.repo / "skills")))
        self.assertFalse(os.path.lexists(excluded))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--powershell", type=Path)
    parser.add_argument("--sandbox-root", type=Path)
    args = parser.parse_args()
    if os.name != "nt":
        raise SystemExit("These junction behavior checks require Windows.")
    configure_runtime(args.powershell, args.sandbox_root)
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(SyncBehaviorTests)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    write_evidence(result)
    raise SystemExit(not result.wasSuccessful())
