"""Stateless metadata tests; all skill inputs live in temporary directories."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("skill_validator", ROOT / "scripts/validate-skills.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


class SkillMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="skill-metadata-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.skill = self.root / "example-skill"
        self.skill.mkdir()

    def write(self, metadata, *, directory=None, bom=False):
        path = (directory or self.skill) / "SKILL.md"
        path.write_text(f"---\n{metadata}\n---\n\nInstructions.\n", encoding="utf-8-sig" if bom else "utf-8")

    def test_valid_yaml_multiline_description_and_bom(self):
        self.write("name: example-skill\ndescription: >\n  Use for a concrete\n  test scenario.", bom=True)
        result = VALIDATOR.read_skill_metadata(self.skill)
        self.assertEqual(result["name"], "example-skill")
        self.assertIn("concrete test", result["description"])

    def test_malformed_yaml_is_not_accepted_by_regex(self):
        self.write("name: example-skill\ndescription: [unfinished")
        with self.assertRaisesRegex(VALIDATOR.SkillValidationError, "Invalid YAML"):
            VALIDATOR.read_skill_metadata(self.skill)

    def test_required_fields_are_nonempty_strings(self):
        for field in ("name", "description"):
            for value in ("", "null", "[]", "123", "true", "'  '"):
                with self.subTest(field=field, value=value):
                    data = {"name": "example-skill", "description": "A useful trigger"}
                    data[field] = value
                    self.write("\n".join(f"{key}: {item}" for key, item in data.items()))
                    with self.assertRaises(VALIDATOR.SkillValidationError):
                        VALIDATOR.read_skill_metadata(self.skill)

    def test_names_are_safe_exact_lowercase_directory_names(self):
        for name in ("Example-skill", "example_skill", "example--skill", "../escape", "other", "a" * 65):
            with self.subTest(name=name):
                self.write(f"name: {name}\ndescription: Valid trigger")
                with self.assertRaises(VALIDATOR.SkillValidationError):
                    VALIDATOR.read_skill_metadata(self.skill)

    def test_duplicate_keys_and_non_mapping_frontmatter_fail(self):
        for metadata in (
            "name: wrong\nname: example-skill\ndescription: Trigger",
            "- name: example-skill\n- description: Trigger",
            "name: example-skill\ndescription: Trigger\nextra:\n  key: one\n  key: two",
        ):
            with self.subTest(metadata=metadata):
                self.write(metadata)
                with self.assertRaises(VALIDATOR.SkillValidationError):
                    VALIDATOR.read_skill_metadata(self.skill)

    def test_import_source_folder_is_flexible_but_name_assertion_is_exact(self):
        directory = self.root / "downloaded-repo-main"
        directory.mkdir()
        self.write("name: example-skill\ndescription: Valid trigger", directory=directory)
        with self.assertRaises(VALIDATOR.SkillValidationError):
            VALIDATOR.read_skill_metadata(directory)
        self.assertEqual(VALIDATOR.read_skill_metadata(directory, check_directory=False)["name"], "example-skill")
        with self.assertRaises(VALIDATOR.SkillValidationError):
            VALIDATOR.read_skill_metadata(directory, check_directory=False, expected_name="renamed")

    def test_missing_frontmatter_and_missing_file_fail(self):
        with self.assertRaises(VALIDATOR.SkillValidationError):
            VALIDATOR.read_skill_metadata(self.skill)
        for text in ("name: example-skill\ndescription: Trigger", "---\nname: example-skill\ndescription: Trigger\n"):
            (self.skill / "SKILL.md").write_text(text, encoding="utf-8")
            with self.assertRaises(VALIDATOR.SkillValidationError):
                VALIDATOR.read_skill_metadata(self.skill)

    def test_failure_is_never_printed_as_pass(self):
        self.write("name: example-skill\ndescription:")
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertFalse(VALIDATOR.validate_skills(self.root))
        self.assertNotIn("PASS: example-skill", output.getvalue())
        self.assertIn("FAIL: example-skill", errors.getvalue())

    def test_empty_or_missing_skills_directory_is_failure(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertFalse(VALIDATOR.validate_skills(self.skill))
            self.assertFalse(VALIDATOR.validate_skills(self.root / "missing"))


if __name__ == "__main__":
    unittest.main()
