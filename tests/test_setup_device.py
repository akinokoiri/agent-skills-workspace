"""Exercise the setup wrapper with an isolated child script, never real sync."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'scripts' / 'setup-device.ps1'
PS = Path(os.environ.get('SystemRoot', r'C:\Windows')) / 'System32/WindowsPowerShell/v1.0/powershell.exe'


@unittest.skipUnless(os.name == 'nt', 'Windows PowerShell wrapper')
class SetupDeviceTests(unittest.TestCase):
    def run_case(self, arguments=(), child_exit=0):
        with tempfile.TemporaryDirectory(prefix='skill-setup-test-') as temp:
            root = Path(temp)
            (root / 'setup-device.ps1').write_bytes(SOURCE.read_bytes())
            (root / 'sync-skills.ps1').write_text(
                "param([switch]$Status,[switch]$DryRun,[switch]$Force,[string]$UserProfilePath)\n"
                "('status=' + [bool]$Status + ';dry=' + [bool]$DryRun + ';force=' + [bool]$Force) | Write-Output\n"
                "if ($UserProfilePath -ne (Join-Path $PSScriptRoot 'user')) { exit 90 }\n"
                f"exit {child_exit}\n", encoding='utf-8')
            env = os.environ.copy()
            for key in ('USERPROFILE', 'HOME', 'APPDATA', 'LOCALAPPDATA', 'TEMP', 'TMP'):
                destination = root / key
                destination.mkdir()
                env[key] = str(destination)
            env['PATH'] = str(root)
            process = subprocess.run(
                [str(PS), '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                 str(root / 'setup-device.ps1'), '-UserProfilePath', str(root / 'user'), *arguments],
                cwd=root, env=env, capture_output=True, text=True, errors='replace', timeout=20)
            return process

    def test_default_does_not_force_conflicts(self):
        result = self.run_case()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('status=False;dry=False;force=False', result.stdout)

    def test_status_is_forwarded_without_mutation_flags(self):
        result = self.run_case(['-StatusOnly'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('status=True;dry=False;force=False', result.stdout)
        self.assertNotIn('SETUP_SYNC_COMPLETE', result.stdout)

    def test_preview_and_explicit_force_are_forwarded(self):
        result = self.run_case(['-DryRun', '-Force'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('status=False;dry=True;force=True', result.stdout)

    def test_child_failure_is_preserved(self):
        result = self.run_case(child_exit=23)
        self.assertEqual(result.returncode, 23)
        self.assertNotIn('SETUP_SYNC_COMPLETE', result.stdout)


if __name__ == '__main__':
    unittest.main()
