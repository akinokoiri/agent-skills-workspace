import importlib.util
import os
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location('policy', Path(__file__).parents[1] / 'scripts/sync-codex-policy.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class PolicyTests(unittest.TestCase):
    def test_full_render_required(self):
        result = SimpleNamespace(returncode=0, stdout=json.dumps([{'text': '<multi_agent_mode>test policy</multi_agent_mode>'}]).encode())
        with patch.object(m.subprocess, 'run', return_value=result):
            m.rendered_check('synthetic', 'test policy', '.')

    def test_truncated_render_rejected(self):
        result = SimpleNamespace(returncode=0, stdout=json.dumps([{'text': '<multi_agent_mode>test\u20262 tokens truncated\u2026policy</multi_agent_mode>'}]).encode())
        with patch.object(m.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'missing/truncated'):
                m.rendered_check('synthetic', 'test full policy', '.')

    def test_conflicting_default_rejected(self):
        result = SimpleNamespace(returncode=0, stdout=json.dumps(['test policy', m.OLD_DEFAULT]).encode())
        with patch.object(m.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(RuntimeError, 'conflicting'):
                m.rendered_check('synthetic', 'test policy', '.')

    def test_preserves_other_settings_and_text(self):
        before = b'# keep\r\nmodel = "test"\r\n[features.multi_agent_v2]\r\nmulti_agent_mode_hint_text = "old"\r\nother = true\r\n[mcp_servers.example.env]\r\nTOKEN = "synthetic-fixture-only"\r\n'
        after = m.build_candidate(before, 'new policy\nnext line')
        self.assertEqual(after, before.replace(b'multi_agent_mode_hint_text = "old"', b'multi_agent_mode_hint_text = "new policy\\nnext line"'))

    def test_absent_section(self):
        after = m.build_candidate(b'model = "test"\n', 'new')
        self.assertEqual(m.current_policy(after), 'new')

    def test_absent_key_existing_section(self):
        before = b'[features.multi_agent_v2]\nother = true\n[desktop]\nvalue = 3\n'
        after = m.build_candidate(before, 'new')
        self.assertTrue(m.parse(after)['features']['multi_agent_v2']['other'])
        self.assertEqual(m.parse(after)['desktop']['value'], 3)

    def test_bom(self):
        after = m.build_candidate(b'\xef\xbb\xbfmodel="test"\r\n', 'new')
        self.assertTrue(after.startswith(b'\xef\xbb\xbf'))

    def test_scalar_conflict(self):
        with self.assertRaises(ValueError):
            m.build_candidate(b'[features]\nmulti_agent_v2=false\n', 'new')

    def test_multiline_refused(self):
        with self.assertRaises(ValueError):
            m.build_candidate(b'[features.multi_agent_v2]\nmulti_agent_mode_hint_text="""old\nvalue"""\n', 'new')

    def test_quoted_section_refused(self):
        with self.assertRaises(ValueError):
            m.build_candidate(b'[features."multi_agent_v2"]\nmulti_agent_mode_hint_text="old"\n', 'new')

    def test_fake_header_in_multiline_string_refused(self):
        before = b'developer_instructions="""\n[features.multi_agent_v2]\nmulti_agent_mode_hint_text="fake"\n"""\n'
        with self.assertRaises(ValueError):
            m.build_candidate(before, 'new')

    def test_idempotent(self):
        once = m.build_candidate(b'', 'new')
        self.assertEqual(once, m.build_candidate(once, 'new'))

    @unittest.skipUnless(os.name == 'nt', 'Windows file sharing and ACL')
    def test_apply_backup(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            path.write_bytes(b'old')
            backup = m.apply_update(path, b'old', b'new', lambda: None)
            self.assertEqual(path.read_bytes(), b'new')
            self.assertEqual(backup.read_bytes(), b'old')

    @unittest.skipUnless(os.name == 'nt', 'Windows file sharing and ACL')
    def test_verification_failure_restores(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            path.write_bytes(b'old')
            with self.assertRaisesRegex(RuntimeError, 'restored'):
                m.apply_update(path, b'old', b'new', lambda: (_ for _ in ()).throw(ValueError()))
            self.assertEqual(path.read_bytes(), b'old')

    @unittest.skipUnless(os.name == 'nt', 'Windows file sharing and ACL')
    def test_concurrent_change_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            path.write_bytes(b'other')
            with self.assertRaisesRegex(RuntimeError, 'changed during'):
                m.apply_update(path, b'old', b'new', lambda: None)
            self.assertEqual(path.read_bytes(), b'other')

    @unittest.skipUnless(os.name == 'nt', 'Windows file sharing and ACL')
    def test_concurrent_change_during_verification_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'config.toml'
            path.write_bytes(b'old')
            def verify():
                with self.assertRaises(PermissionError):
                    path.write_bytes(b'other')
                self.assertEqual(path.read_bytes(), b'new')
            m.apply_update(path, b'old', b'new', verify)
            self.assertEqual(path.read_bytes(), b'new')


if __name__ == '__main__':
    unittest.main()
