#!/usr/bin/env python3
"""Bounded, non-interactive, allowlisted SSH operations for /ssh."""

import argparse
import hashlib
import json
import os
import re
import select
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Dict, FrozenSet, List, Mapping, NoReturn, Optional, Tuple, TypedDict, cast

DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 300
CONNECT_TIMEOUT = 10
MAX_LINES = 200
MAX_BYTES = 64 * 1024
TERMINATE_GRACE = 2
KILL_GRACE = 2
ENV_RE = re.compile(r"^[a-z][a-z0-9_]*$")
VARIABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
USER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
HOSTKEYALIAS_RE = re.compile(r"^(?:[A-Za-z0-9][A-Za-z0-9._:-]*|\[[A-Za-z0-9][A-Za-z0-9._:-]*\]:[1-9][0-9]{0,4})$")
SAFE_FOLDER_RE = re.compile(r"^/(?:[A-Za-z0-9._-]+/)*[A-Za-z0-9._-]*$")
SAFE_LOG_RE = re.compile(r"^[A-Za-z0-9._-]+\.log$")
LARAVEL_CONFIG_KEYS: FrozenSet[str] = frozenset({"app.environment", "app.debug", "cache.default", "queue.default", "database.default", "session.driver"})
GENERIC_READ_ONLY: FrozenSet[Tuple[str, ...]] = frozenset({
    ("pwd",), ("git", "status"), ("git", "status", "--short"),
    ("git", "status", "--branch"), ("git", "status", "--short", "--branch"),
})
LARAVEL_CONFIRMED: FrozenSet[Tuple[str, ...]] = frozenset({
    ("git", "pull", "--ff-only"), ("php", "artisan", "migrate", "--force"),
    ("php", "artisan", "cache:clear"), ("php", "artisan", "config:clear"),
    ("php", "artisan", "queue:restart"),
})
# Immutable registry is enforcement source and capabilities source. Do not derive policy from config.
class ProfilePolicy(TypedDict):
    read_only: FrozenSet[Tuple[str, ...]]
    confirmed: FrozenSet[Tuple[str, ...]]
    ls_flags: FrozenSet[str]
    inspect_env: bool
    inspect_config_keys: FrozenSet[str]
    log_tail: Optional["LogTailPolicy"]


class LogTailPolicy(TypedDict):
    max_lines: int
    path_prefix: str
    filename_pattern: str


PROFILE_REGISTRY: Mapping[str, ProfilePolicy] = MappingProxyType({
    "generic": cast(ProfilePolicy, MappingProxyType({"read_only": GENERIC_READ_ONLY, "confirmed": frozenset(), "ls_flags": frozenset({"-a", "-l", "-la", "-al", "--all", "--long"}), "inspect_env": False, "inspect_config_keys": frozenset(), "log_tail": None})),
    "laravel": cast(ProfilePolicy, MappingProxyType({"read_only": GENERIC_READ_ONLY, "confirmed": LARAVEL_CONFIRMED, "ls_flags": frozenset({"-a", "-l", "-la", "-al", "--all", "--long"}), "inspect_env": True, "inspect_config_keys": LARAVEL_CONFIG_KEYS, "log_tail": cast(LogTailPolicy, MappingProxyType({"max_lines": MAX_LINES, "path_prefix": "storage/logs/", "filename_pattern": SAFE_LOG_RE.pattern}))})),
})
ASSIGNMENT_RE = re.compile(r"(?i)\b([A-Z0-9_]*(?:TOKEN|KEY|SECRET|PASSWORD)[A-Z0-9_]*)=([^\s]+)")
BEARER_RE = re.compile(r"(?i)(authorization\s*:\s*bearer\s+)[^\s]+")
CONFIG_SECRET_RE = re.compile(r"(?im)^([^\n]*(?:token|key|secret|password|credential|authorization)[^\n]*?)(?:\s*(?:=>|:)\s*|\s{2,})\S.*$")
SSH_KEYGEN_FINGERPRINT_RE = re.compile(r"(?m)^\d+\s+(SHA256:[A-Za-z0-9+/]{43})\s+")


@dataclass(frozen=True)
class Target:
    alias: str
    hostname: str
    user: str
    port: str
    hostkeyalias: str
    folder: str
    known_hosts_file: str
    profile: str


def fail(message: str) -> NoReturn:
    print(f"error: {message}", file=sys.stderr)
    raise SystemExit(2)


def project_root() -> str:
    root = ""
    try:
        root = subprocess.run(["git", "rev-parse", "--show-toplevel"], text=True, capture_output=True, check=True, timeout=CONNECT_TIMEOUT).stdout.strip()
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        fail("no Git project root from current directory")
    return root


def untracked_regular_file(root: str, name: str) -> Optional[Path]:
    """Return root-local untracked regular file, or None when absent."""
    path = Path(root) / name
    if path.is_symlink():
        fail(f"refusing symlinked project {name}")
    if not path.exists():
        return None
    if not path.is_file():
        fail(f"project {name} is not a regular file")
    if name == ".ssh-skill.json" and os.name == "posix":
        try:
            if path.stat().st_mode & 0o077:
                fail("project .ssh-skill.json must be owner-only (chmod 600)")
        except OSError:
            fail("cannot verify project .ssh-skill.json permissions")
    try:
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", "--", name], cwd=root, text=True, capture_output=True, timeout=CONNECT_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        fail(f"cannot verify project {name} tracking")
    if tracked.returncode == 0:
        fail(f"refusing Git-tracked project {name}")
    return path


def project_env(root: str) -> Dict[str, str]:
    env_path = untracked_regular_file(root, ".env")
    if env_path is None:
        fail("missing project environment file")
    values: Dict[str, str] = {}
    lines: List[str] = []
    try:
        lines = env_path.read_text(encoding="utf-8").splitlines()
    except OSError:
        fail("cannot read project .env")
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if separator and re.fullmatch(r"SSH_[A-Z0-9_]+", key.strip()):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
                value = value[1:-1]
            values[key.strip()] = value
    return values


def config_targets(root: str) -> Optional[Dict[str, Dict[str, str]]]:
    path = untracked_regular_file(root, ".ssh-skill.json")
    if path is None:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        fail("invalid .ssh-skill.json")
    if not isinstance(data, dict) or set(data) != {"targets"} or not isinstance(data["targets"], dict) or not data["targets"]:
        fail("invalid .ssh-skill.json schema")
    targets: Dict[str, Dict[str, str]] = {}
    for environment, entry in data["targets"].items():
        if not isinstance(environment, str) or not ENV_RE.fullmatch(environment) or not isinstance(entry, dict) or set(entry) != {"host", "folder", "profile"}:
            fail("invalid .ssh-skill.json target schema")
        if not all(isinstance(entry[key], str) for key in entry) or not HOST_RE.fullmatch(entry["host"]) or not SAFE_FOLDER_RE.fullmatch(entry["folder"]) or entry["profile"] not in PROFILE_REGISTRY:
            fail("unsafe .ssh-skill.json target")
        targets[environment] = {key: entry[key] for key in ("host", "folder", "profile")}
    return targets


def ssh_effective(alias: str) -> Dict[str, str]:
    if not HOST_RE.fullmatch(alias):
        fail("unsafe SSH_HOST alias")
    try:
        result = subprocess.run(["ssh", "-G", alias], text=True, capture_output=True, timeout=CONNECT_TIMEOUT)
    except (OSError, subprocess.TimeoutExpired):
        fail("cannot resolve effective SSH target")
        raise AssertionError("unreachable")
    if result.returncode:
        fail("cannot resolve effective SSH target")
    effective: Dict[str, str] = {}
    for line in result.stdout.splitlines():
        key, separator, value = line.partition(" ")
        if separator:
            effective[key.lower()] = value.strip()
    required = ("hostname", "user", "port")
    if any(not effective.get(key) for key in required):
        fail("incomplete effective SSH target")
    if not HOST_RE.fullmatch(effective["hostname"]) or not USER_RE.fullmatch(effective["user"]):
        fail("unsafe effective SSH target")
    try:
        if not 1 <= int(effective["port"]) <= 65535:
            fail("unsafe effective SSH target")
    except ValueError:
        fail("unsafe effective SSH target")
    hostkeyalias = effective.get("hostkeyalias", "none")
    if hostkeyalias == "none":
        hostkeyalias = effective["hostname"] if effective["port"] == "22" else f"[{effective['hostname']}]:{effective['port']}"
    if not HOSTKEYALIAS_RE.fullmatch(hostkeyalias):
        fail("unsafe effective host-key alias")
    return {**effective, "hostkeyalias": hostkeyalias}


def target(environment: str) -> Target:
    if not ENV_RE.fullmatch(environment):
        fail("invalid environment; use lowercase letters, digits, and underscores only")
    root = project_root()
    configured = config_targets(root)
    if configured is not None:
        if environment not in configured:
            fail("unknown target in .ssh-skill.json")
        selection = configured[environment]
    else:
        # Legacy .env keeps existing Laravel-only projects working.
        values = project_env(root)
        folder_key = f"SSH_{environment.upper()}_FOLDER"
        if not values.get("SSH_HOST") or not values.get(folder_key):
            missing = [key for key in ("SSH_HOST", folder_key) if not values.get(key)]
            fail("missing required .env keys: " + ", ".join(missing))
        selection = {"host": values["SSH_HOST"], "folder": values[folder_key], "profile": "laravel"}
        if not SAFE_FOLDER_RE.fullmatch(selection["folder"]):
            fail("unsafe target folder")
    effective = ssh_effective(selection["host"])
    return Target(selection["host"], effective["hostname"], effective["user"], effective["port"], effective["hostkeyalias"], selection["folder"], effective.get("userknownhostsfile", ""), selection["profile"])


def canonical_policy(policy: ProfilePolicy) -> str:
    """Stable serialization of every enforcement field used by a profile."""
    payload = {
        "confirmed": sorted(policy["confirmed"]),
        "inspect_config_keys": sorted(policy["inspect_config_keys"]),
        "inspect_env": policy["inspect_env"],
        "log_tail": dict(policy["log_tail"]) if policy["log_tail"] else None,
        "ls_flags": sorted(policy["ls_flags"]),
        "read_only": sorted(policy["read_only"]),
    }
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def fingerprint(target: Target) -> str:
    policy = PROFILE_REGISTRY[target.profile]
    policy_digest = hashlib.sha256(canonical_policy(policy).encode("utf-8")).hexdigest()
    selection = {
        "alias": target.alias,
        "folder": target.folder,
        "hostkeyalias": target.hostkeyalias,
        "hostname": target.hostname,
        "known_hosts_file": target.known_hosts_file,
        "policy_digest": policy_digest,
        "port": target.port,
        "profile": target.profile,
        "user": target.user,
    }
    return hashlib.sha256(json.dumps(selection, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def require_selected_target(args: argparse.Namespace, selected: Target) -> None:
    if not getattr(args, "expected_fingerprint", None):
        fail("effective target binding required")
    if args.expected_fingerprint != fingerprint(selected):
        fail("selected target no longer matches effective SSH target")


def remote(folder: str, argv: List[str]) -> str:
    return f"cd -- {shlex.quote(folder)} && exec {shlex.join(argv)}"


def ssh_argv(target: Target, command: str) -> List[str]:
    return ["ssh", "-T", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=yes", "-o", "UpdateHostKeys=no", "-o", "ClearAllForwardings=yes", "-o", "ForwardAgent=no", "-o", "ForwardX11=no", "-o", "ForwardX11Trusted=no", "-o", "PermitLocalCommand=no", "-o", "ControlMaster=no", "-o", "ControlPath=none", "-o", "ControlPersist=no", "-o", f"ConnectTimeout={CONNECT_TIMEOUT}", "-o", f"HostKeyAlias={target.hostkeyalias}", "-l", target.user, "-p", target.port, target.alias, command]


def clean_output(output: bytes) -> str:
    text = output.decode("utf-8", errors="replace")
    text = "".join(char for char in text if char in "\n\t" or (char.isprintable() and char != "\x7f"))
    text = ASSIGNMENT_RE.sub(r"\1=[REDACTED]", text)
    text = BEARER_RE.sub(r"\1[REDACTED]", text)
    return CONFIG_SECRET_RE.sub(r"\1 [REDACTED]", text)


def terminate_process(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=TERMINATE_GRACE)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=KILL_GRACE)
        except subprocess.TimeoutExpired:
            pass


def wait_to_deadline(process: subprocess.Popen[bytes], deadline: float) -> bool:
    """Wait only through deadline; terminate and kill on expiry. Returns timeout state."""
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        terminate_process(process)
        return True
    try:
        process.wait(timeout=remaining)
        return False
    except subprocess.TimeoutExpired:
        terminate_process(process)
        return True


def run_ssh(target: Target, argv: List[str], timeout: int) -> int:
    try:
        process = subprocess.Popen(ssh_argv(target, remote(target.folder, argv)), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError:
        print("error: cannot start ssh", file=sys.stderr)
        return 127
    assert process.stdout is not None
    output, lines, capped, timed_out = bytearray(), 0, False, False
    deadline = time.monotonic() + timeout
    while len(output) < MAX_BYTES:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([process.stdout], [], [], remaining)[0]:
            timed_out = True
            break
        chunk = os.read(process.stdout.fileno(), min(4096, MAX_BYTES - len(output)))
        if not chunk:
            break
        allowed = MAX_LINES - lines
        if chunk.count(b"\n") > allowed:
            boundary = -1
            for _ in range(allowed):
                boundary = chunk.find(b"\n", boundary + 1)
            output.extend(chunk[:boundary + 1])
            capped = True
            break
        output.extend(chunk)
        lines += chunk.count(b"\n")
    if len(output) >= MAX_BYTES:
        capped = True
    if capped:
        terminate_process(process)
    else:
        timed_out = wait_to_deadline(process, deadline) or timed_out
    text = clean_output(bytes(output))
    if text:
        print(text, end="" if text.endswith("\n") else "\n")
    if capped:
        print("[output capped; local SSH terminated]")
        return 124
    if timed_out:
        print(f"error: command timed out after {timeout} seconds", file=sys.stderr)
        return 124
    return process.returncode


def operation(profile: str, argv: List[str]) -> Optional[str]:
    policy = PROFILE_REGISTRY[profile]
    if tuple(argv) in policy["read_only"]:
        return "read-only"
    if argv and argv[0] == "ls" and all(flag in policy["ls_flags"] for flag in argv[1:]):
        return "read-only"
    log_tail = policy["log_tail"]
    if log_tail and len(argv) == 4 and argv[:2] == ["tail", "-n"] and argv[2].isdigit() and 0 < int(argv[2]) <= int(log_tail["max_lines"]) and argv[3].startswith(str(log_tail["path_prefix"])) and SAFE_LOG_RE.fullmatch(argv[3][len(str(log_tail["path_prefix"])):]):
        return "read-only"
    if tuple(argv) in policy["confirmed"]:
        return "confirmed"
    return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="mode", required=True)
    capabilities = subs.add_parser("capabilities")
    capabilities.add_argument("profile", choices=sorted(PROFILE_REGISTRY))
    for name in ("validate", "host-key"):
        subs.add_parser(name).add_argument("environment")
    for name in ("run", "inspect-env", "inspect-config", "trust-host-key"):
        command = subs.add_parser(name)
        command.add_argument("environment")
        command.add_argument("--expected-fingerprint")
        if name == "run":
            command.add_argument("--confirmed", action="store_true")
            command.add_argument("--confirmed-timeout", action="store_true")
            command.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
            command.add_argument("command", nargs="+")
        elif name == "inspect-env":
            command.add_argument("variables", nargs="+")
        elif name == "inspect-config":
            command.add_argument("key")
        else:
            command.add_argument("--confirmed", action="store_true")
            command.add_argument("--fingerprint", required=True)
    return parser.parse_args()


def capability_descriptor(profile: str) -> Dict[str, object]:
    """Public, complete view of immutable operation enforcement for one profile."""
    policy = PROFILE_REGISTRY[profile]
    operations = ([{"argv": list(argv), "confirmation": "none"} for argv in sorted(policy["read_only"])] +
                  [{"argv": list(argv), "confirmation": "required"} for argv in sorted(policy["confirmed"])] +
                  [{"argv": ["ls"], "allowed_flags": sorted(policy["ls_flags"]), "paths_allowed": False, "confirmation": "none"}])
    if policy["log_tail"]:
        log_tail = policy["log_tail"]
        operations.append({"argv": ["tail", "-n", "<line-count>", "<log-path>"], "confirmation": "none", "line_count": {"minimum": 1, "maximum": log_tail["max_lines"]}, "path_prefix": log_tail["path_prefix"], "filename_pattern": log_tail["filename_pattern"]})
    return {
        "profile": profile,
        "operations": operations,
        "inspect_env": {"argv": ["inspect-env", "<variable>", "..."], "allowed": policy["inspect_env"], "confirmation": "none", "variable_pattern": VARIABLE_RE.pattern if policy["inspect_env"] else None},
        "inspect_config": {"argv": ["inspect-config", "<safe-key>"], "allowed": bool(policy["inspect_config_keys"]), "confirmation": "none", "safe_keys": sorted(policy["inspect_config_keys"])},
    }


def persist_verified_host_key(selected: Target, expected: str) -> int:
    if not re.fullmatch(r"SHA256:[A-Za-z0-9+/]{43}", expected):
        fail("invalid host-key fingerprint")
    try:
        scan = subprocess.run(["ssh-keyscan", "-T", str(CONNECT_TIMEOUT), "-p", selected.port, selected.hostname], text=True, capture_output=True, timeout=CONNECT_TIMEOUT + TERMINATE_GRACE)
    except (OSError, subprocess.TimeoutExpired):
        print("error: cannot scan host key", file=sys.stderr)
        return 1
    if scan.returncode != 0 or not scan.stdout:
        print("error: cannot scan host key", file=sys.stderr)
        return scan.returncode or 1
    verified = []
    for line in scan.stdout.splitlines():
        try:
            result = subprocess.run(["ssh-keygen", "-lf", "-"], input=line + "\n", text=True, capture_output=True, timeout=CONNECT_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired):
            continue
        match = SSH_KEYGEN_FINGERPRINT_RE.search(result.stdout)
        if result.returncode == 0 and match and expected == match.group(1):
            parts = line.split(maxsplit=2)
            if len(parts) == 3:
                verified.append(f"{selected.hostkeyalias} {parts[1]} {parts[2]}\n")
    if len(verified) != 1:
        fail("candidate scan did not contain exactly one verified key")
    paths = shlex.split(selected.known_hosts_file)
    if len(paths) != 1 or not paths[0].startswith("/") or paths[0] == "/dev/null":
        fail("unsafe effective user known-hosts file")
    known_hosts = Path(paths[0])
    if known_hosts.is_symlink():
        fail("refusing symlinked user known-hosts file")
    try:
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY
        flags |= getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(known_hosts, flags, 0o600)
        with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
            handle.write(verified[0])
    except OSError:
        print("error: cannot persist verified host key", file=sys.stderr)
        return 1
    print(f"persisted verified host key for {selected.hostkeyalias}")
    return 0


def main() -> int:
    args = parse_args()
    if args.mode == "capabilities":
        print(json.dumps(capability_descriptor(args.profile), sort_keys=True))
        return 0
    selected = target(args.environment)
    if args.mode == "validate":
        print(f"environment={args.environment} profile={selected.profile} endpoint={selected.user}@{selected.hostname}:{selected.port} hostkeyalias={selected.hostkeyalias} folder={selected.folder} fingerprint={fingerprint(selected)}")
        return run_ssh(selected, ["pwd"], CONNECT_TIMEOUT)
    if args.mode == "host-key":
        print(f"Host key identity: {selected.hostkeyalias}. Candidate keys are untrusted; nothing is persisted.")
        try:
            scan = subprocess.run(["ssh-keyscan", "-T", str(CONNECT_TIMEOUT), "-p", selected.port, selected.hostname], text=True, capture_output=True, timeout=CONNECT_TIMEOUT + TERMINATE_GRACE)
        except (OSError, subprocess.TimeoutExpired):
            print("error: cannot scan host key", file=sys.stderr)
            return 1
        if scan.returncode != 0 or not scan.stdout:
            print("error: cannot scan host key", file=sys.stderr)
            return scan.returncode or 1
        try:
            result = subprocess.run(["ssh-keygen", "-lf", "-"], input=scan.stdout, text=True, capture_output=True, timeout=CONNECT_TIMEOUT)
        except (OSError, subprocess.TimeoutExpired):
            print("error: cannot fingerprint host key", file=sys.stderr)
            return 1
        print(clean_output(result.stdout.encode()), end="")
        return result.returncode
    require_selected_target(args, selected)
    if args.mode == "trust-host-key":
        if not args.confirmed:
            fail("persisting host key requires exact user confirmation")
        return persist_verified_host_key(selected, args.fingerprint)
    if args.mode == "run":
        kind = operation(selected.profile, args.command)
        if kind is None:
            fail("operation not allowlisted")
        if not 0 < args.timeout <= MAX_TIMEOUT:
            fail(f"timeout must be 1..{MAX_TIMEOUT} seconds")
        if kind == "confirmed" and not args.confirmed:
            fail("named operation requires exact user confirmation")
        if args.timeout > DEFAULT_TIMEOUT and not args.confirmed_timeout:
            fail("longer timeout requires explicit duration confirmation")
        print(f"target={args.environment} profile={selected.profile} endpoint={selected.user}@{selected.hostname}:{selected.port} hostkeyalias={selected.hostkeyalias} folder={selected.folder} classification={kind} timeout={args.timeout}s")
        return run_ssh(selected, args.command, args.timeout)
    if args.mode == "inspect-env":
        if not PROFILE_REGISTRY[selected.profile]["inspect_env"]:
            fail("profile does not allow environment inspection")
        if any(not VARIABLE_RE.fullmatch(variable) for variable in args.variables):
            fail("invalid variable name")
        # Deliberately fixed helper script; user input reaches only positional parameters.
        script = 'for name; do if printenv "$name" >/dev/null; then if [ -n "$(printenv "$name")" ]; then state=nonempty; else state=empty; fi; printf "%s present=yes %s preview=[REDACTED]\\n" "$name" "$state"; else printf "%s present=no state=missing preview=[REDACTED]\\n" "$name"; fi; done'
        return run_ssh(selected, ["sh", "-c", script, "inspect-env", *args.variables], DEFAULT_TIMEOUT)
    if args.key not in PROFILE_REGISTRY[selected.profile]["inspect_config_keys"]:
        fail("unknown or sensitive config key")
    return run_ssh(selected, ["php", "artisan", "config:show", args.key], DEFAULT_TIMEOUT)


if __name__ == "__main__":
    raise SystemExit(main())
