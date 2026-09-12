"""Apply one Codex policy key; Python 3.11+, no third-party packages.

Default: status only. --dry-run checks runtime compatibility in an isolated
temporary CODEX_HOME. --apply also backs up and updates the local config.
Complex TOML layouts are deliberately rejected instead of being rewritten.
Raw configuration and rendered prompts are never printed or saved to a report.
"""
import argparse
import contextlib
import copy
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import tomllib

KEY = "multi_agent_mode_hint_text"
TABLE = "features.multi_agent_v2"
OLD_DEFAULT = "Do not spawn sub-agents unless the user or applicable AGENTS.md/skill instructions explicitly ask for sub-agents, delegation, or parallel agent work."


def digest(data):
    return hashlib.sha256(data).hexdigest()


def parse(data):
    return tomllib.loads(data.decode("utf-8-sig"))


def current_policy(data):
    value = parse(data).get("features", {}).get("multi_agent_v2", {})
    if not isinstance(value, dict):
        raise ValueError("multi_agent_v2 uses a scalar layout; preserve it and review compatibility manually")
    return value.get(KEY)


def build_candidate(data, policy):
    before = parse(data)
    current_policy(data)
    text = data.decode("utf-8-sig")
    newline = "\r\n" if "\r\n" in text else "\n"
    assignment = KEY + " = " + json.dumps(policy, ensure_ascii=False)
    headers = list(re.finditer(r"(?m)^\[features\.multi_agent_v2\][ \t]*(?:#[^\r\n]*)?\r?$", text))
    if len(headers) > 1:
        raise ValueError("ambiguous target section")
    if headers:
        start = headers[0].end()
        next_header = re.search(r"(?m)^\[", text[start:])
        end = start + next_header.start() if next_header else len(text)
        section = text[start:end]
        keys = list(re.finditer(r"(?m)^[ \t]*" + KEY + r"[ \t]*=[^\r\n]*", section))
        if len(keys) > 1:
            raise ValueError("ambiguous target key")
        if keys:
            item = keys[0]
            # Multi-line values need a TOML-aware editor; never remove only their first line.
            line_value = tomllib.loads(item.group(0))[KEY]
            if not isinstance(line_value, str):
                raise ValueError("target key must be a string")
            section = section[:item.start()] + assignment + section[item.end():]
        else:
            section = section.rstrip("\r\n") + newline + assignment + newline + newline
        updated = text[:start] + section + text[end:]
    else:
        updated = text.rstrip("\r\n") + newline + newline + "[" + TABLE + "]" + newline + assignment + newline
    encoded = (b"\xef\xbb\xbf" if data.startswith(b"\xef\xbb\xbf") else b"") + updated.encode("utf-8")
    expected = copy.deepcopy(before)
    expected.setdefault("features", {}).setdefault("multi_agent_v2", {})[KEY] = policy
    if parse(encoded) != expected:
        raise ValueError("candidate changes settings outside the managed key")
    return encoded


def rendered_check(executable, policy, cwd, env=None):
    args = [executable, "debug", "prompt-input", "Delegation configuration verification only."]
    result = subprocess.run(args, cwd=cwd, env=env, capture_output=True, timeout=60)
    # Parse the JSON, so string escaping cannot cause a false mismatch.
    if result.returncode:
        raise RuntimeError("runtime prompt check failed; raw output suppressed")
    try:
        payload = json.loads(result.stdout.decode("utf-8-sig"))
    except (ValueError, UnicodeError):
        raise RuntimeError("runtime prompt output format unsupported; raw output suppressed") from None
    def strings(value):
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                yield from strings(item)
        elif isinstance(value, list):
            for item in value:
                yield from strings(item)
    content = list(strings(payload))
    if not any(policy in item for item in content) or any(OLD_DEFAULT in item for item in content):
        raise RuntimeError("full policy missing/truncated or conflicting default remains in rendered prompt")


def runtime_probe(executable, policy):
    with tempfile.TemporaryDirectory(prefix="codex-policy-probe-") as directory:
        root = Path(directory)
        isolated = root / "codex-home"
        isolated.mkdir()
        (isolated / "config.toml").write_bytes(build_candidate(b"", policy))
        env = os.environ.copy()
        env["CODEX_HOME"] = str(isolated)
        rendered_check(executable, policy, root, env)


@contextlib.contextmanager
def locked_config(path):
    # Windows sharing denies other writers and replacements while allowing the
    # Codex verifier to read. Writing through this handle retains the file ACL.
    if os.name != "nt":
        raise RuntimeError("apply currently supports Windows only; status and dry-run remain portable")
    import ctypes
    from ctypes import wintypes
    import msvcrt
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    handle = create(str(path), 0xC0000000, 1, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise RuntimeError("cannot exclusively lock config for writing; close other configuration writers and retry")
    try:
        descriptor = msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
    except Exception:
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle(handle)
        raise
    with os.fdopen(descriptor, "r+b") as stream:
        yield stream


def write_locked(stream, data):
    stream.seek(0)
    stream.write(data)
    stream.truncate()
    stream.flush()
    os.fsync(stream.fileno())


def copy_backup_acl(source, target):
    env = os.environ.copy()
    # PowerShell 7's inherited module path can break Windows PowerShell 5.1.
    for key in list(env):
        if key.lower() == "psmodulepath":
            del env[key]
    env["CODEX_POLICY_ACL_SOURCE"] = str(source)
    env["CODEX_POLICY_ACL_TARGET"] = str(target)
    command = "$ErrorActionPreference='Stop'; $a=Get-Acl -LiteralPath $env:CODEX_POLICY_ACL_SOURCE; Set-Acl -LiteralPath $env:CODEX_POLICY_ACL_TARGET -AclObject $a; $b=Get-Acl -LiteralPath $env:CODEX_POLICY_ACL_TARGET; $d=@(Compare-Object -ReferenceObject @($a.Access) -DifferenceObject @($b.Access) -Property IdentityReference,FileSystemRights,AccessControlType,IsInherited,InheritanceFlags,PropagationFlags); if($a.Owner -ne $b.Owner -or $a.Group -ne $b.Group -or $a.AreAccessRulesProtected -ne $b.AreAccessRulesProtected -or $d.Count -ne 0){exit 2}"
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command], env=env, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError("backup ACL verification failed; original config unchanged")


def apply_update(path, before, candidate, verify):
    with locked_config(path) as stream:
        if stream.read() != before:
            raise RuntimeError("configuration changed during inspection; retry after reviewing it")
        stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
        backup = path.with_name(path.name + ".bak-delegation-" + stamp)
        backup.touch(exist_ok=False)
        # Set permissions before copying any potentially sensitive bytes.
        copy_backup_acl(path, backup)
        backup.write_bytes(before)
        if backup.read_bytes() != before:
            raise RuntimeError("backup verification failed; original config unchanged")
        try:
            write_locked(stream, candidate)
            verify()
        except Exception:
            try:
                write_locked(stream, before)
            except Exception:
                raise RuntimeError("update and restoration failed; restore the same-directory backup manually") from None
            raise RuntimeError("post-update verification failed; original configuration restored") from None
        return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--codex", help="absolute path to this device's actual Codex executable")
    parser.add_argument("--policy", type=Path, default=Path(__file__).resolve().parents[1] / "config/codex/delegation-policy.txt")
    args = parser.parse_args()
    home = Path(os.environ.get("CODEX_HOME") or Path.home() / ".codex").resolve()
    config = home / "config.toml"
    if config.is_symlink() or not config.is_file():
        raise ValueError("expected an existing regular config.toml; review links or new-device setup manually")
    before = config.read_bytes()
    policy = args.policy.read_text(encoding="utf-8-sig").strip()
    if not policy:
        raise ValueError("empty policy")
    matches = current_policy(before) == policy
    print(json.dumps({"config": str(config), "matches": matches, "policy_sha256": digest(policy.encode())}))
    if not args.apply and not args.dry_run:
        return
    candidate = build_candidate(before, policy)
    executable = args.codex
    if not executable or not Path(executable).is_absolute() or not Path(executable).is_file():
        raise ValueError("specify --codex with the absolute path of this device's actual runtime")
    runtime_probe(executable, policy)
    print("ISOLATED_RUNTIME_PROBE_PASSED")
    if args.dry_run:
        print("DRY_RUN_PASSED: local config unchanged")
        return
    with tempfile.TemporaryDirectory(prefix="codex-policy-verify-") as directory:
        def verify():
            if current_policy(config.read_bytes()) != policy:
                raise RuntimeError("policy changed before verification")
            rendered_check(executable, policy, directory)
            if current_policy(config.read_bytes()) != policy:
                raise RuntimeError("policy changed during verification")
        if matches:
            verify()
            print("ALREADY_CURRENT: rendered prompt verified; no write")
        else:
            backup = apply_update(config, before, candidate, verify)
            print(json.dumps({"result": "APPLIED_AND_RENDER_VERIFIED", "backup": str(backup)}))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        # TOML and subprocess diagnostics can contain local configuration values.
        safe = str(error) if type(error) in (RuntimeError, ValueError) else "operation failed; raw diagnostic suppressed"
        print("ERROR: " + safe, file=sys.stderr)
        sys.exit(1)
