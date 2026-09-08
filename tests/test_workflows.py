"""Windows workflow integration tests, using fresh local Git remotes and fake sync.

No real checkout workflow, network remote, user config, skill manager or mounts are
used. Every test has a new fixture; Git permits the file protocol only.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import yaml


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"
GIT = shutil.which("git")
SCRIPT_NAMES = ("pull-sync.ps1", "import-skill.ps1", "Workflow.Common.psm1", "validate-skills.py")


@unittest.skipUnless(os.name == "nt" and GIT, "Requires Windows PowerShell 5.1 and Git")
class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-workflow-test-")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.remote, self.seed, self.repo = (self.base / name for name in ("remote.git", "seed", "device"))
        self.tools = self.base / "fake-tools"
        self.tools.mkdir()
        self.log = self.base / "sync.log"
        self.manager_log = self.base / "manager.log"
        # Local PyYAML may be installed in the user's site-packages. Copy only
        # this dependency so the child retains a fully isolated user profile.
        python_libs = self.base / "python-libs"
        shutil.copytree(Path(yaml.__file__).parent, python_libs / "yaml", ignore=shutil.ignore_patterns("__pycache__"))
        self.env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
        for key in ("HOME", "USERPROFILE", "APPDATA", "LOCALAPPDATA", "TEMP", "TMP"):
            directory = self.base / key
            directory.mkdir()
            self.env[key] = str(directory)
        config = self.base / "empty-git-config"
        config.write_text("", encoding="utf-8")
        self.env.update({
            "GIT_CONFIG_GLOBAL": str(config), "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_ALLOW_PROTOCOL": "file", "GIT_TERMINAL_PROMPT": "0",
            "SYNC_TEST_LOG": str(self.log), "SYNC_TEST_EXIT": "0",
            "MANAGER_TEST_LOG": str(self.manager_log),
            "PYTHONPATH": str(python_libs), "PYTHONNOUSERSITE": "1",
            "PATH": os.pathsep.join((str(self.tools), str(Path(GIT).parent), str(POWERSHELL.parent),
                                     str(Path(os.environ["SystemRoot"]) / "System32"), str(Path(sys.executable).parent))),
        })
        for name in ("skills-manager.cmd", "skills-manager-cli.cmd", "sm.cmd"):
            (self.tools / name).write_text('@echo off\r\necho CALLED>>"%MANAGER_TEST_LOG%"\r\nexit /b 97\r\n', encoding="ascii")
        self.git(self.base, "init", "--bare", "--initial-branch=main", str(self.remote))
        self.git(self.base, "init", "--initial-branch=main", str(self.seed))
        self.configure(self.seed)
        (self.seed / "scripts").mkdir()
        (self.seed / "skills/base-skill").mkdir(parents=True)
        for name in SCRIPT_NAMES:
            shutil.copyfile(ROOT / "scripts" / name, self.seed / "scripts" / name)
        (self.seed / "scripts/sync-skills.ps1").write_text(
            "param([switch]$Status)\n"
            "if ($Status) { $operation='STATUS' } else { $operation='MOUNT' }\n"
            "[IO.File]::AppendAllText($env:SYNC_TEST_LOG, $operation + [Environment]::NewLine)\n"
            "Write-Output ('FAKE_SYNC:' + $operation)\n"
            "exit ([int]$env:SYNC_TEST_EXIT)\n", encoding="utf-8")
        (self.seed / "skills/base-skill/SKILL.md").write_text(
            "---\nname: base-skill\ndescription: Existing fixture skill\n---\nold body\n", encoding="utf-8")
        (self.seed / ".gitignore").write_text("backups/\n__pycache__/\n", encoding="utf-8")
        (self.seed / "notes.txt").write_text("initial\n", encoding="utf-8")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "fixture initial")
        self.git(self.seed, "remote", "add", "origin", str(self.remote))
        self.git(self.seed, "push", "-u", "origin", "main")
        self.git(self.base, "clone", str(self.remote), str(self.repo))
        self.configure(self.repo)

    def tearDown(self):
        self.assertFalse(self.manager_log.exists(), "No workflow may invoke any Skills Manager")

    def configure(self, path):
        self.git(path, "config", "user.name", "Fixture Tester")
        self.git(path, "config", "user.email", "fixture@example.invalid")
        self.git(path, "config", "core.autocrlf", "false")
        self.git(path, "config", "commit.gpgsign", "false")

    def git(self, path, *args, check=True):
        result = subprocess.run([GIT, "-C", str(path), *args], env=self.env, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=30)
        if check and result.returncode:
            self.fail(f"Fixture Git failed: {args[0]}: {result.stdout} {result.stderr}")
        return result.stdout.strip() if check else result

    def head(self, path=None):
        return self.git(path or self.repo, "rev-parse", "HEAD")

    def run_script(self, name, *args):
        return subprocess.run([str(POWERSHELL), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                               str(self.repo / "scripts" / name), *map(str, args)], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, errors="replace", timeout=45)

    def pull(self, *args):
        return self.run_script("pull-sync.ps1", *args)

    def import_skill(self, source=None, *args):
        options = ["-PythonExecutable", sys.executable]
        if source is not None:
            options += ["-SourcePath", str(source)]
        return self.run_script("import-skill.ps1", *options, *args)

    def source(self, name="new-skill", body="new body"):
        source = self.base / ("source-" + name)
        source.mkdir()
        (source / "SKILL.md").write_text(f"---\nname: {name}\ndescription: A fixture import trigger\n---\n{body}\n", encoding="utf-8")
        (source / "resources").mkdir()
        (source / "resources/example.txt").write_text("keep resource\n", encoding="utf-8")
        return source

    def remote_change(self):
        (self.seed / "remote-only.txt").write_text("remote advance\n", encoding="utf-8")
        self.git(self.seed, "add", ".")
        self.git(self.seed, "commit", "-m", "remote advance")
        self.git(self.seed, "push", "origin", "main")
        return self.head(self.seed)

    def assert_failure(self, result, marker):
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn(marker, result.stdout + result.stderr)

    def install_failing_git(self, verb):
        # Inputs are fixture paths, and the actual real Git executable is captured
        # before the fake-tool PATH is installed. This never calls a network remote.
        wrapper = self.tools / "git.cmd"
        wrapper.write_text(
            '@echo off\r\n'
            f'if "%~3"=="{verb}" (\r\n'
            '  echo failed https://fixture-user:fixture-secret@example.invalid/repo?token=fixture-query-secret 1>&2\r\n'
            '  exit /b 31\r\n)\r\n'
            f'"{GIT}" %*\r\nexit /b %errorlevel%\r\n', encoding="ascii")

    def junction(self, path, target):
        env = self.env.copy()
        env.update({"FIXTURE_LINK": str(path), "FIXTURE_TARGET": str(target)})
        result = subprocess.run([str(POWERSHELL), "-NoProfile", "-Command",
                                 "$ErrorActionPreference='Stop'; New-Item -ItemType Junction -Path $env:FIXTURE_LINK -Target $env:FIXTURE_TARGET | Out-Null"],
                                cwd=self.base, env=env, capture_output=True, text=True, errors="replace", timeout=15)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_pull_defaults_to_git_only(self):
        expected = self.remote_change()
        result = self.pull()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.head(), expected)
        self.assertIn("UPDATE_COMPLETE", result.stdout)
        self.assertFalse(self.log.exists())

    def test_explicit_sync_and_compatibility_no_sync(self):
        result = self.pull("-Sync")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.log.read_text(), "MOUNT\n")
        self.log.unlink()
        result = self.pull("-NoSync")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.log.exists())
        self.assert_failure(self.pull("-Sync", "-NoSync"), "UPDATE_COMPLETE")

    def test_dirty_tracked_and_untracked_files_block_update_without_touching_stash(self):
        (self.repo / "notes.txt").write_text("unrelated stash\n", encoding="utf-8")
        self.git(self.repo, "stash", "push", "-m", "fixture unrelated")
        before_stash, before_head = self.git(self.repo, "stash", "list"), self.head()
        (self.repo / "notes.txt").write_text("local edits\n", encoding="utf-8")
        (self.repo / "untracked.txt").write_text("keep me\n", encoding="utf-8")
        self.remote_change()
        result = self.pull("-Sync")
        self.assert_failure(result, "UPDATE_COMPLETE")
        self.assertEqual(self.head(), before_head)
        self.assertEqual(self.git(self.repo, "stash", "list"), before_stash)
        self.assertEqual((self.repo / "notes.txt").read_text(), "local edits\n")
        self.assertEqual((self.repo / "untracked.txt").read_text(), "keep me\n")
        self.assertFalse(self.log.exists())

    def test_untracked_file_alone_blocks_update(self):
        (self.repo / "untracked.txt").write_text("keep\n", encoding="utf-8")
        before = self.head()
        self.remote_change()
        self.assert_failure(self.pull(), "UPDATE_COMPLETE")
        self.assertEqual(self.head(), before)

    def test_existing_stash_is_not_restored_during_clean_update(self):
        (self.repo / "notes.txt").write_text("stash stays out\n", encoding="utf-8")
        self.git(self.repo, "stash", "push", "-m", "fixture unrelated")
        before = self.git(self.repo, "stash", "list")
        self.remote_change()
        result = self.pull()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git(self.repo, "stash", "list"), before)
        self.assertEqual((self.repo / "notes.txt").read_text(), "initial\n")

    def test_divergence_fails_without_rebase_or_sync(self):
        (self.repo / "local-only.txt").write_text("local commit\n", encoding="utf-8")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "local diverging commit")
        before = self.head()
        self.remote_change()
        self.assert_failure(self.pull("-Sync"), "UPDATE_COMPLETE")
        self.assertEqual(self.head(), before)
        self.assertFalse((self.repo / "remote-only.txt").exists())
        self.assertFalse(self.log.exists())

    def test_status_does_not_fetch_pull_refresh_index_or_mount(self):
        self.remote_change()
        (self.repo / "untracked.txt").write_text("local\n", encoding="utf-8")
        before = self.head()
        index_before = (self.repo / ".git/index").read_bytes()
        self.assertFalse((self.repo / ".git/FETCH_HEAD").exists())
        result = self.pull("-Status")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("STATUS_COMPLETE", result.stdout)
        self.assertEqual(self.head(), before)
        self.assertEqual((self.repo / ".git/index").read_bytes(), index_before)
        self.assertFalse((self.repo / ".git/FETCH_HEAD").exists())
        self.assertEqual(self.log.read_text(), "STATUS\n")
        self.log.unlink()
        self.assertEqual(self.pull("-Status", "-NoSync").returncode, 0)
        self.assertFalse(self.log.exists())

    def test_git_failure_stops_before_sync_and_redacts_credentials(self):
        before = self.head()
        self.install_failing_git("pull")
        result = self.pull("-Sync")
        self.assert_failure(result, "UPDATE_COMPLETE")
        self.assertEqual(self.head(), before)
        self.assertFalse(self.log.exists())
        combined = result.stdout + result.stderr
        self.assertIn("REDACTED", combined)
        self.assertNotIn("fixture-secret", combined)
        self.assertNotIn("fixture-query-secret", combined)

    def test_sync_failure_is_not_reported_as_update_complete(self):
        expected = self.remote_change()
        self.env["SYNC_TEST_EXIT"] = "23"
        result = self.pull("-Sync")
        self.assert_failure(result, "UPDATE_COMPLETE")
        self.assertEqual(self.head(), expected)

    def test_non_main_branch_is_rejected(self):
        self.git(self.repo, "checkout", "-b", "feature")
        self.assert_failure(self.pull("-Sync"), "UPDATE_COMPLETE")
        self.assertFalse(self.log.exists())

    def test_missing_upstream_is_rejected(self):
        self.git(self.repo, "branch", "--unset-upstream")
        self.assert_failure(self.pull("-Sync"), "UPDATE_COMPLETE")
        self.assertFalse(self.log.exists())

    def test_import_is_local_by_default_and_copies_resources_without_git_metadata(self):
        source = self.source()
        (source / ".git").mkdir()
        (source / ".git/private-config").write_text("not a skill resource", encoding="utf-8")
        before, remote_before = self.head(), self.head(self.remote)
        result = self.import_skill(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("IMPORT_COMPLETE", result.stdout)
        self.assertIn("published=False", result.stdout)
        self.assertEqual(self.head(), before)
        self.assertEqual(self.head(self.remote), remote_before)
        target = self.repo / "skills/new-skill"
        self.assertEqual((target / "resources/example.txt").read_text(), "keep resource\n")
        self.assertFalse((target / ".git").exists())
        self.assertFalse(self.log.exists())

    def test_invalid_metadata_and_name_mismatch_do_not_import(self):
        source = self.source()
        (source / "SKILL.md").write_text("---\nname: new-skill\ndescription: [broken\n---\n", encoding="utf-8")
        self.assert_failure(self.import_skill(source, "-Sync"), "IMPORT_COMPLETE")
        (source / "SKILL.md").write_text("---\nname: new-skill\ndescription: Valid trigger\n---\n", encoding="utf-8")
        self.assert_failure(self.import_skill(source, "-Name", "different", "-Sync"), "IMPORT_COMPLETE")
        self.assertFalse((self.repo / "skills/new-skill").exists())
        self.assertFalse(self.log.exists())

    def test_force_keeps_previous_bytes_and_self_import_is_safe(self):
        original = (self.repo / "skills/base-skill/SKILL.md").read_bytes()
        source = self.source("base-skill", "replacement")
        self.assert_failure(self.import_skill(source), "IMPORT_COMPLETE")
        result = self.import_skill(source, "-Force")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        manifests = list((self.repo / "backups").glob("import-*/restore-manifest.json"))
        record = json.loads(manifests[0].read_text(encoding="utf-8-sig"))
        self.assertEqual((Path(record["previous"]) / "SKILL.md").read_bytes(), original)
        current = (self.repo / "skills/base-skill/SKILL.md").read_bytes()
        result = self.import_skill(self.repo / "skills/base-skill", "-Force")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.repo / "skills/base-skill/SKILL.md").read_bytes(), current)

    def test_import_from_existing_global_junction_keeps_source(self):
        target = self.repo / "skills/base-skill"
        source = self.base / "global-skill-entry"
        self.junction(source, target)
        before = (target / "SKILL.md").read_bytes()
        result = self.import_skill(source, "-Force")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((source / "SKILL.md").read_bytes(), before)
        self.assertEqual((target / "SKILL.md").read_bytes(), before)

    def test_child_junction_is_rejected_without_replacing_target_or_touching_external_files(self):
        source = self.source("base-skill")
        external = self.base / "external"
        external.mkdir()
        sentinel = external / "keep.txt"
        sentinel.write_text("unchanged\n", encoding="utf-8")
        self.junction(source / "linked-content", external)
        before = (self.repo / "skills/base-skill/SKILL.md").read_bytes()
        self.assert_failure(self.import_skill(source, "-Force", "-Sync"), "IMPORT_COMPLETE")
        self.assertEqual((self.repo / "skills/base-skill/SKILL.md").read_bytes(), before)
        self.assertEqual(sentinel.read_text(), "unchanged\n")
        self.assertFalse(self.log.exists())

    def test_destination_junction_is_never_overwritten(self):
        source = self.source()
        destination = self.repo / "skills/new-skill"
        self.junction(destination, source)
        before = (source / "SKILL.md").read_bytes()
        self.assert_failure(self.import_skill(source, "-Force"), "IMPORT_COMPLETE")
        self.assertEqual((source / "SKILL.md").read_bytes(), before)
        self.assertEqual((destination / "SKILL.md").read_bytes(), before)

    def test_import_push_fast_forwards_first_then_publishes(self):
        source = self.source()
        self.remote_change()
        result = self.import_skill(source, "-Push", "-Sync")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.head(), self.head(self.remote))
        self.assertTrue((self.repo / "remote-only.txt").exists())
        self.assertEqual(self.git(self.repo, "status", "--porcelain"), "")
        self.assertIn("PUBLISH_COMPLETE", result.stdout)
        self.assertEqual(self.log.read_text(), "MOUNT\n")

    def test_import_push_rejects_dirty_checkout_before_modifying_skill(self):
        source = self.source()
        (self.repo / "notes.txt").write_text("keep local edit\n", encoding="utf-8")
        before = self.head()
        self.assert_failure(self.import_skill(source, "-Push", "-Sync"), "PUBLISH_COMPLETE")
        self.assertEqual(self.head(), before)
        self.assertFalse((self.repo / "skills/new-skill").exists())
        self.assertEqual((self.repo / "notes.txt").read_text(), "keep local edit\n")
        self.assertEqual(self.git(self.repo, "stash", "list"), "")
        self.assertFalse(self.log.exists())

    def test_import_push_does_not_publish_unrelated_local_commits(self):
        source = self.source()
        (self.repo / "unpublished.txt").write_text("requires separate authorization\n", encoding="utf-8")
        self.git(self.repo, "add", ".")
        self.git(self.repo, "commit", "-m", "unpublished local commit")
        before, remote_before = self.head(), self.head(self.remote)
        result = self.import_skill(source, "-Push", "-Sync")
        self.assert_failure(result, "PUBLISH_COMPLETE")
        self.assertEqual(self.head(), before)
        self.assertEqual(self.head(self.remote), remote_before)
        self.assertFalse((self.repo / "skills/new-skill").exists())
        self.assertFalse(self.log.exists())

    def test_skill_named_previous_does_not_collide_with_backup_directory(self):
        source = self.source("previous", "first version")
        result = self.import_skill(source)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        old = (self.repo / "skills/previous/SKILL.md").read_bytes()
        (source / "SKILL.md").write_text("---\nname: previous\ndescription: Trigger\n---\nsecond version\n", encoding="utf-8")
        result = self.import_skill(source, "-Force")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        records = [json.loads(path.read_text(encoding="utf-8-sig")) for path in (self.repo / "backups").glob("import-*/restore-manifest.json")]
        previous = [item for item in records if item["previous"]][0]
        self.assertEqual((Path(previous["previous"]) / "SKILL.md").read_bytes(), old)
        self.assertIn("second version", (self.repo / "skills/previous/SKILL.md").read_text())
        self.assertFalse((self.repo / "skills/previous/previous").exists())

    def test_local_git_clone_import_never_publishes_implicitly(self):
        source = self.source()
        self.git(self.base, "init", "--initial-branch=main", str(source))
        self.configure(source)
        self.git(source, "add", ".")
        self.git(source, "commit", "-m", "source fixture")
        before = self.head(self.remote)
        result = self.import_skill(None, "-GitUrl", str(source))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.head(self.remote), before)
        self.assertTrue((self.repo / "skills/new-skill/SKILL.md").exists())
        self.assertFalse((self.repo / "skills/new-skill/.git").exists())
        self.assertIn("Clone snapshot retained", result.stdout)
        self.assertFalse(self.log.exists())

    def test_missing_python_executable_fails_before_import(self):
        source = self.source()
        result = self.run_script("import-skill.ps1", "-SourcePath", str(source), "-PythonExecutable", str(self.base / "missing-python.exe"), "-Sync")
        self.assert_failure(result, "IMPORT_COMPLETE")
        self.assertFalse((self.repo / "skills/new-skill").exists())
        self.assertFalse(self.log.exists())

    def test_import_clone_failure_is_sanitized_and_stops(self):
        self.install_failing_git("clone")
        result = self.import_skill(None, "-GitUrl", str(self.base / "missing.git"), "-Sync")
        self.assert_failure(result, "IMPORT_COMPLETE")
        self.assertFalse(self.log.exists())
        self.assertNotIn("fixture-secret", result.stdout + result.stderr)
        self.assertNotIn("fixture-query-secret", result.stdout + result.stderr)

    def test_import_pull_failure_leaves_original_skill_untouched(self):
        source = self.source("base-skill", "replacement")
        old = (self.repo / "skills/base-skill/SKILL.md").read_bytes()
        self.install_failing_git("pull")
        result = self.import_skill(source, "-Push", "-Force", "-Sync")
        self.assert_failure(result, "PUBLISH_COMPLETE")
        self.assertEqual((self.repo / "skills/base-skill/SKILL.md").read_bytes(), old)
        self.assertFalse(self.log.exists())

    def test_commit_failure_preserves_local_import_without_pushing_or_syncing(self):
        source = self.source()
        remote_before = self.head(self.remote)
        self.install_failing_git("commit")
        result = self.import_skill(source, "-Push", "-Sync")
        self.assert_failure(result, "PUBLISH_COMPLETE")
        self.assertIn("IMPORT_PARTIAL", result.stdout)
        self.assertEqual(self.head(self.remote), remote_before)
        self.assertTrue((self.repo / "skills/new-skill/SKILL.md").exists())
        self.assertFalse(self.log.exists())

    def test_push_failure_keeps_commit_without_claiming_publish_or_syncing(self):
        source = self.source()
        before, remote_before = self.head(), self.head(self.remote)
        self.install_failing_git("push")
        result = self.import_skill(source, "-Push", "-Sync")
        self.assert_failure(result, "PUBLISH_COMPLETE")
        self.assertNotEqual(self.head(), before)
        self.assertEqual(self.head(self.remote), remote_before)
        self.assertIn("IMPORT_PARTIAL", result.stdout)
        self.assertFalse(self.log.exists())

    def test_import_sync_failure_reports_partial_local_success(self):
        source = self.source()
        self.env["SYNC_TEST_EXIT"] = "23"
        result = self.import_skill(source, "-Sync")
        self.assert_failure(result, "IMPORT_COMPLETE")
        self.assertIn("IMPORT_PARTIAL", result.stdout)
        self.assertTrue((self.repo / "skills/new-skill/SKILL.md").exists())

    def test_import_sync_options_are_mutually_exclusive(self):
        source = self.source()
        self.assert_failure(self.import_skill(source, "-Sync", "-NoSync"), "IMPORT_COMPLETE")
        self.assertFalse((self.repo / "skills/new-skill").exists())


if __name__ == "__main__":
    unittest.main()
