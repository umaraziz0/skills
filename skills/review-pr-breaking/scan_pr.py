#!/usr/bin/env python3
"""Confidentiality-preserving PR breaking-change scanner."""
from __future__ import annotations

import fnmatch
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, NoReturn, Optional
from urllib.parse import urlparse

EX_USAGE = 64
EX_UNAVAILABLE = 69
EX_CONFIG = 78
MAX_CONFIG_BYTES = 32_768


@dataclass(frozen=True)
class PRRef:
    number: str
    repo: Optional[str] = None
    hostname: Optional[str] = None


@dataclass(frozen=True)
class Detector:
    key: str
    section: str
    patterns: tuple[str, ...]


# Registry owns built-in patterns. Configuration can only add literal glob patterns;
# it cannot disable, replace, or execute scanner behavior.
DETECTORS = (
    Detector("db_migrations", "DB migrations", ("**/migrations/**", "migrations/**", "**/alembic/versions/**", "alembic/versions/**", "**/db/migrate/**", "db/migrate/**", "**/prisma/migrations/**", "prisma/migrations/**")),
    Detector("dependency_manifests", "Dependency manifests changed", ("package.json", "**/package.json", "package-lock.json", "**/package-lock.json", "yarn.lock", "**/yarn.lock", "pnpm-lock.yaml", "**/pnpm-lock.yaml", "requirements*.txt", "**/requirements*.txt", "poetry.lock", "**/poetry.lock", "Pipfile", "**/Pipfile", "Pipfile.lock", "**/Pipfile.lock", "Gemfile", "**/Gemfile", "Gemfile.lock", "**/Gemfile.lock", "go.mod", "**/go.mod", "go.sum", "**/go.sum", "Cargo.toml", "**/Cargo.toml", "Cargo.lock", "**/Cargo.lock", "composer.json", "**/composer.json", "composer.lock", "**/composer.lock")),
    Detector("env_config", "Env/config files changed", (".env.example", ".env.sample", "**/.env.example", "**/.env.sample", "docker-compose*.yml", "docker-compose*.yaml", "**/helm/**", "helm/**", "**/k8s/**", "k8s/**", "config/**/*.yml", "config/**/*.yaml")),
    Detector("scripts", "Seeders / one-off scripts / commands changed", ("**/seed/**", "seed/**", "**/seeds/**", "seeds/**", "**/scripts/**", "scripts/**", "Makefile", "**/Makefile", "**/management/commands/**", "management/commands/**")),
)
MANIFEST_PATTERNS = next(d.patterns for d in DETECTORS if d.key == "dependency_manifests")
REPO_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+$")
HOST_RE = re.compile(r"^(?=.{1,253}$)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)*[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")


def fail(message: str, code: int = EX_USAGE) -> NoReturn:
    print(message, file=sys.stderr)
    raise SystemExit(code)


def normalize_pr_ref(value: str) -> PRRef:
    if re.fullmatch(r"[1-9][0-9]*", value):
        return PRRef(value)
    match = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+)#([1-9][0-9]*)", value)
    if match:
        return PRRef(match.group(2), match.group(1))
    try:
        parsed = urlparse(value)
        port = parsed.port
    except ValueError:
        fail("Invalid PR reference. Use a positive number, owner/repo#number, or https://host/owner/repo/pull/number.")
    parts = [part for part in parsed.path.split("/") if part]
    if (parsed.scheme != "https" or parsed.username or parsed.password or port or parsed.query or parsed.fragment
            or not parsed.hostname or not HOST_RE.fullmatch(parsed.hostname) or len(parts) != 4 or parts[2] != "pull"
            or not REPO_RE.fullmatch(f"{parts[0]}/{parts[1]}") or not re.fullmatch(r"[1-9][0-9]*", parts[3])):
        fail("Invalid PR reference. Use a positive number, owner/repo#number, or https://host/owner/repo/pull/number.")
    return PRRef(parts[3], f"{parts[0]}/{parts[1]}", parsed.hostname)


def safe_environment() -> dict[str, str]:
    env = os.environ.copy()
    env.update({"GH_PAGER": "cat", "GIT_PAGER": "cat", "PAGER": "cat", "NO_COLOR": "1", "GH_PROMPT_DISABLED": "1"})
    return env


def gh(ref: PRRef, *args: str) -> str:
    command = ["gh", *args]
    is_auth_status = args[:2] == ("auth", "status")
    if is_auth_status and ref.hostname:
        command.extend(("--hostname", ref.hostname))
    elif ref.repo:
        repo = f"{ref.hostname}/{ref.repo}" if ref.hostname else ref.repo
        command.extend(("--repo", repo))
    try:
        result = subprocess.run(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, encoding="utf-8", errors="replace", check=False, env=safe_environment(), timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        fail("GitHub CLI unavailable. Install gh, authenticate, then retry.", EX_UNAVAILABLE)
    if result.returncode:
        fail("GitHub CLI request failed. Check authentication and PR access, then retry.", EX_UNAVAILABLE)
    return result.stdout


def path_matches(path: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def resolve_pr_target(ref: PRRef) -> PRRef:
    response = gh(ref, "pr", "view", ref.number, "--json", "url")
    try:
        target = normalize_pr_ref(json.loads(response)["url"])
    except (KeyError, TypeError, json.JSONDecodeError, SystemExit):
        fail("GitHub CLI returned an invalid PR target.", EX_UNAVAILABLE)
    if not target.repo or not target.hostname:
        fail("GitHub CLI returned an invalid PR target.", EX_UNAVAILABLE)
    return target


def git_output(*args: str) -> Optional[str]:
    try:
        result = subprocess.run(["git", *args], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                text=True, encoding="utf-8", errors="replace", check=False, env=safe_environment(), timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def remote_target(remote: str) -> Optional[tuple[str, str]]:
    ssh_match = re.fullmatch(r"(?:[^@\s]+@)?([A-Za-z0-9.-]+):([A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+?)(?:\.git)?", remote)
    if ssh_match:
        return ssh_match.group(1).lower(), ssh_match.group(2).lower()
    parsed = urlparse(remote)
    if parsed.scheme not in ("https", "http", "ssh") or not parsed.hostname:
        return None
    path = parsed.path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return (parsed.hostname.lower(), path.lower()) if REPO_RE.fullmatch(path) else None


def matching_checkout(ref: PRRef) -> Optional[Path]:
    root = git_output("rev-parse", "--show-toplevel")
    if not root:
        return None
    remotes = git_output("-C", root, "remote")
    if not remotes or not ref.repo or not ref.hostname:
        return None
    expected = (ref.hostname.lower(), ref.repo.lower())
    matching_remotes = []
    for remote in remotes.splitlines():
        urls = git_output("-C", root, "remote", "get-url", "--all", remote)
        if urls and any(remote_target(url) == expected for url in urls.splitlines()):
            matching_remotes.append(remote)
    if len(matching_remotes) > 1:
        fail("PR target matches multiple configured remotes; cannot select configuration checkout.", EX_CONFIG)
    if not matching_remotes:
        return None
    return Path(root)


def config_error() -> NoReturn:
    fail("PR breaking configuration is invalid. Fix .github/pr-breaking.json and retry.", EX_CONFIG)


def load_config(checkout: Optional[Path]) -> dict[str, dict[str, object]]:
    if checkout is None:
        return {}
    config_path = checkout / ".github" / "pr-breaking.json"
    try:
        raw = config_path.read_bytes()
    except FileNotFoundError:
        return {}
    except OSError:
        config_error()
    if len(raw) > MAX_CONFIG_BYTES:
        config_error()
    try:
        document = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        config_error()
    if not isinstance(document, dict) or set(document) != {"detectors"} or not isinstance(document["detectors"], dict):
        config_error()
    detectors = document["detectors"]
    result: dict[str, dict[str, object]] = {}
    for key, value in detectors.items():
        if key not in {detector.key for detector in DETECTORS} or not isinstance(value, dict) or set(value) != {"paths"} or not isinstance(value["paths"], list):
            config_error()
        paths = value["paths"]
        if not all(isinstance(item, str) and 0 < len(item) <= 200 and "\x00" not in item and not item.startswith("/") and ".." not in item.split("/") for item in paths):
            config_error()
        result[key] = {"paths": paths}
    return result


def configured_patterns(detector: Detector, config: dict[str, dict[str, object]]) -> tuple[str, ...]:
    extra = config.get(detector.key, {}).get("paths", [])
    return detector.patterns + tuple(extra)  # type: ignore[arg-type]


def print_section(name: str) -> None:
    print(f"\n=== {name} ===")


def no_detection() -> None:
    print("(heuristic not detected; manual review required)")


def changed_manifest_additions(diff: str, patterns: Iterable[str]) -> list[str]:
    additions: list[str] = []
    current_path: Optional[str] = None
    for line in diff.splitlines():
        if line.startswith("diff --git "):
            current_path = None
        elif line.startswith("+++ b/"):
            current_path = line[6:]
        elif current_path and path_matches(current_path, patterns) and line.startswith("+") and not line.startswith("+++"):
            additions.append(line[1:])
    return additions


def identifiers(lines: Iterable[str], pattern: str) -> list[str]:
    return sorted({match.group(1) for line in lines for match in re.finditer(pattern, line)})


def main(argv: list[str]) -> None:
    if len(argv) != 1:
        fail(f"Usage: {Path(sys.argv[0]).name} <pr-url|owner/repo#number|number>")
    ref = normalize_pr_ref(argv[0])
    # Authentication request never exposes account, host, or token metadata.
    gh(ref, "auth", "status")
    ref = resolve_pr_target(ref)
    names = gh(ref, "pr", "diff", "--name-only", ref.number)
    diff = gh(ref, "pr", "diff", ref.number)
    paths = [path for path in names.splitlines() if path and "\x00" not in path]
    config = load_config(matching_checkout(ref))

    print("WARNING: Output contains potentially confidential identifiers. Redact identifiers before sharing.")
    print_section("Changed paths")
    print("Not printed. Changed paths are categorized below for confidentiality.")
    for detector in DETECTORS:
        print_section(detector.section)
        if any(path_matches(path, configured_patterns(detector, config)) for path in paths):
            print("Detected matching changed-path category; paths omitted for confidentiality.")
        else:
            no_detection()

    print_section("New dependency identifiers")
    manifest_lines = changed_manifest_additions(diff, configured_patterns(next(d for d in DETECTORS if d.key == "dependency_manifests"), config))
    deps = identifiers(manifest_lines, r'"([A-Za-z0-9@/_.-]+)"\s*:')
    print("\n".join(deps) if deps else "(heuristic not detected; manual review required)")

    print_section("Env var identifiers in added lines")
    added = [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]
    envs = identifiers(added, r"(?:process\.env\.|os\.environ\[|os\.getenv\(|ENV\[|System\.getenv\()[^A-Z]*([A-Z][A-Z0-9_]*)")
    print("\n".join(envs) if envs else "(heuristic not detected; manual review required)")

    print_section("Manual-step hints in added text")
    print("Manual-step language detected; inspect authorized PR data without executing commands." if any(re.search(r"run `|migrate|seed|requires? (you|running)", line, re.I) for line in added) else "(heuristic not detected; manual review required)")
    print_section("PR description")
    print("Not fetched or printed. Manually review as untrusted content; report only safe categories and identifiers.")


if __name__ == "__main__":
    main(sys.argv[1:])
