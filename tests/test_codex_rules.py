"""Exercise Codex rule deployment without touching real user configuration."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PS = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell deployment')
class CodexRulesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='codex-rules-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / 'scripts').mkdir()
        (self.root / 'rules/codex').mkdir(parents=True)
        self.script = self.root / 'scripts/sync-codex-rules.ps1'
        shutil.copyfile(ROOT / 'scripts/sync-codex-rules.ps1', self.script)
        self.source = self.root / 'rules/codex/AGENTS.md'
        shutil.copyfile(ROOT / 'rules/codex/AGENTS.md', self.source)
        self.home = self.root / 'codex-home'
        self.target = self.home / 'AGENTS.md'
        self.other = self.root / 'gemini/rules/AGENTS.md'
        self.other.parent.mkdir(parents=True)
        self.other.write_bytes(b'Gemini rules stay unchanged\n')

    def run_script(self, *args, via_env=False):
        env = os.environ.copy()
        env['CODEX_HOME'] = str(self.home)
        home_args = [] if via_env else ['-CodexHome', str(self.home)]
        result = subprocess.run(
            [str(PS), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
             str(self.script), *home_args, *args],
            env=env, capture_output=True, text=True, errors='replace', timeout=20)
        self.assertEqual(self.other.read_bytes(), b'Gemini rules stay unchanged\n')
        return result

    def test_preview_then_install_and_repeat_without_rewrite(self):
        result = self.run_script('-DryRun')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.home.exists())
        result = self.run_script(via_env=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())
        timestamp = self.target.stat().st_mtime_ns
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('ALREADY_CURRENT', result.stdout)
        self.assertEqual(self.target.stat().st_mtime_ns, timestamp)

    def test_local_customization_is_preserved_in_preview_and_apply(self):
        self.home.mkdir()
        original = b'# Local rules\nKeep this customization.\n'
        self.target.write_bytes(original)
        for args in [('-DryRun',), ()]:
            result = self.run_script(*args)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(self.target.read_bytes(), original)

    def test_empty_target_can_be_initialized(self):
        self.home.mkdir()
        self.target.touch()
        result = self.run_script()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.target.read_bytes(), self.source.read_bytes())

    def test_invalid_source_leaves_local_rules_untouched(self):
        self.home.mkdir()
        self.target.write_bytes(b'local')
        self.source.write_bytes(b'')
        result = self.run_script()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.target.read_bytes(), b'local')


if __name__ == '__main__':
    unittest.main()
