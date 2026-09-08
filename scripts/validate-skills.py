#!/usr/bin/env python3
"""Validate skill metadata for local imports and CI; no files are changed."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import sys
try:
    import yaml
except ImportError:
    yaml = None

class SkillValidationError(ValueError):
    """The skill cannot be safely identified from its metadata."""

if yaml is not None:
    class UniqueKeyLoader(yaml.SafeLoader):
        """Reject duplicate keys instead of silently accepting the last value."""
        def construct_mapping(self, node, deep=False):
            self.flatten_mapping(node)
            result = {}
            for key_node, value_node in node.value:
                key = self.construct_object(key_node, deep=deep)
                try:
                    duplicate = key in result
                except TypeError as exc:
                    raise SkillValidationError("YAML mapping keys must be scalar values") from exc
                if duplicate:
                    raise SkillValidationError(f"Duplicate YAML key: {key}")
                result[key] = self.construct_object(value_node, deep=deep)
            return result

def read_skill_metadata(skill_dir, *, check_directory=True, expected_name=None):
    if yaml is None:
        raise SkillValidationError("PyYAML is required: from the repository root, run python -m pip install -r requirements-dev.txt")
    directory = Path(skill_dir)
    try:
        content = (directory / "SKILL.md").read_text(encoding="utf-8-sig")
    except (OSError, UnicodeError) as exc:
        raise SkillValidationError(f"Cannot read UTF-8 SKILL.md: {exc}") from exc
    match = re.match(r"\A---[ \t]*\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", content, re.DOTALL)
    if not match:
        raise SkillValidationError("SKILL.md must start with a complete YAML frontmatter block")
    try:
        metadata = yaml.load(match.group(1), Loader=UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise SkillValidationError(f"Invalid YAML frontmatter: {exc}") from exc
    if not isinstance(metadata, dict):
        raise SkillValidationError("YAML frontmatter must be a mapping")
    for field in ("name", "description"):
        if not isinstance(metadata.get(field), str) or not metadata[field].strip():
            raise SkillValidationError(f"{field} must be a non-empty string")
    name = metadata["name"]
    if len(name) > 64 or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name):
        raise SkillValidationError("name must use lowercase letters, digits and single hyphens, at most 64 characters")
    if check_directory and name != directory.name:
        raise SkillValidationError(f"Declared name {name!r} differs from directory {directory.name!r}")
    if expected_name is not None and name != expected_name:
        raise SkillValidationError(f"Requested name {expected_name!r} differs from declared name {name!r}")
    return {"name": name, "description": metadata["description"]}

def validate_skills(skills_dir="skills"):
    directory = Path(skills_dir)
    if not directory.is_dir():
        print(f"ERROR: Skills directory not found: {directory}", file=sys.stderr)
        return False
    children = sorted(p for p in directory.iterdir() if p.is_dir() and not p.name.startswith("."))
    if not children:
        print(f"ERROR: No skill directories found: {directory}", file=sys.stderr)
        return False
    failures = []
    for child in children:
        try:
            read_skill_metadata(child)
        except SkillValidationError as exc:
            failures.append((child.name, str(exc)))
            print(f"FAIL: {child.name}: {exc}", file=sys.stderr)
        else:
            print(f"PASS: {child.name}")
    print(f"Validated {len(children)} skills; failures={len(failures)}")
    return not failures

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skills_dir", nargs="?", default="skills")
    parser.add_argument("--skill-dir", help="Validate one skill directory")
    parser.add_argument("--source", action="store_true", help="Permit a different source folder name before import")
    parser.add_argument("--expected-name")
    parser.add_argument("--json", action="store_true", help="Emit name/description JSON for one skill")
    args = parser.parse_args(argv)
    if not args.skill_dir:
        if args.source or args.expected_name or args.json:
            parser.error("--source, --expected-name and --json require --skill-dir")
        return 0 if validate_skills(args.skills_dir) else 1
    try:
        metadata = read_skill_metadata(args.skill_dir, check_directory=not args.source, expected_name=args.expected_name)
    except SkillValidationError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(metadata, ensure_ascii=True))
    else:
        print(f"PASS: {metadata['name']}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
