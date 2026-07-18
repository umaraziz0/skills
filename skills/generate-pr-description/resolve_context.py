#!/usr/bin/env python3
"""Read-only context resolver for generate-pr-description."""

import argparse
import json
import os
import stat
import subprocess
import sys


TEMPLATE_FILES = (
    ".github/pull_request_template.md", "PULL_REQUEST_TEMPLATE.md",
    "pull_request_template.md", "docs/pull_request_template.md",
)
TEMPLATE_DIRS = (".github/PULL_REQUEST_TEMPLATE", "PULL_REQUEST_TEMPLATE",
                 "docs/PULL_REQUEST_TEMPLATE")


class GitError(RuntimeError):
    pass


def git(repo, *args, required=True):
    completed = subprocess.run(["git", "-C", repo, *args], text=True,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               check=False)
    if required and completed.returncode:
        raise GitError(completed.stderr.strip() or "git command failed")
    return completed.stdout.strip() if completed.returncode == 0 else None


def commit_oid(repo, ref):
    if not ref or any(char in ref for char in ("\x00", "\n", "\r")):
        return None
    return git(repo, "rev-parse", "--verify", "--quiet", "--end-of-options",
               ref + "^{commit}", required=False)


def base_record(repo, ref, source):
    oid = commit_oid(repo, ref)
    if not oid:
        return None
    record = {"ref": ref, "commit": oid, "source": source}
    if ref.startswith("refs/remotes/"):
        parts = ref[len("refs/remotes/"):].split("/", 1)
        if len(parts) == 2:
            record["remote"], record["branch"] = parts
    return record


def branch_context(repo):
    head = commit_oid(repo, "HEAD")
    if not head:
        raise GitError("HEAD does not resolve to a commit")
    branch = git(repo, "symbolic-ref", "--quiet", "--short", "HEAD", required=False)
    return {"commit": head, "branch": branch, "detached": branch is None}


def upstream_ref(repo, branch):
    if not branch:
        return None
    return git(repo, "for-each-ref", "--format=%(upstream)",
               "refs/heads/" + branch, required=False) or None


def remote_refs(repo):
    return [ref for ref in (git(repo, "for-each-ref", "--format=%(refname)",
                                "refs/remotes") or "").splitlines()
            if not ref.endswith("/HEAD")]


def remote_names(repo):
    return sorted({ref[len("refs/remotes/"):].split("/", 1)[0]
                   for ref in remote_refs(repo)})


def all_candidates(repo, branch=None):
    refs = (git(repo, "for-each-ref", "--format=%(refname)", "refs/heads",
                "refs/remotes") or "").splitlines()
    if branch:
        refs = [ref for ref in refs if ref == "refs/heads/" + branch or
                ref.startswith("refs/remotes/") and ref.endswith("/" + branch)]
    return [record for record in (base_record(repo, ref, "available") for ref in sorted(refs))
            if record and not record["ref"].endswith("/HEAD")]


def base_selection(reason, candidates):
    return {"status": "selection_required", "reason": reason,
            "base": None, "base_candidates": candidates}


def resolve_base(repo, supplied, head):
    if supplied is None:
        upstream = base_record(repo, upstream_ref(repo, head["branch"]), "upstream")
        if not upstream or not upstream.get("remote"):
            return base_selection("Current branch has no remote-tracking upstream.", [])
        target = git(repo, "symbolic-ref", "--quiet",
                     "refs/remotes/" + upstream["remote"] + "/HEAD", required=False)
        record = base_record(repo, target, "remote_default")
        if record:
            return {"status": "resolved", "base": record, "base_candidates": []}
        return base_selection("Upstream remote has no valid symbolic remote HEAD.", [])

    value = supplied.strip()
    if value in {"remote counterpart", "remote tracking", "upstream"}:
        record = base_record(repo, upstream_ref(repo, head["branch"]), "upstream")
        return ({"status": "resolved", "base": record, "base_candidates": []} if record
                else base_selection("Current branch has no valid upstream.", []))

    remotes = remote_names(repo)
    if value in remotes:
        record = base_record(repo, upstream_ref(repo, head["branch"]), "upstream")
        if record and record.get("remote") == value:
            return {"status": "resolved", "base": record, "base_candidates": []}
        return base_selection("Bare remote is not a branch; select a branch on that remote.",
                              [item for item in all_candidates(repo)
                               if item.get("remote") == value])

    words = value.split(None, 1)
    if len(words) == 2 and words[0] in remotes:
        record = base_record(repo, "refs/remotes/" + words[0] + "/" + words[1], "requested")
        return ({"status": "resolved", "base": record, "base_candidates": []} if record else
                {"status": "error", "error": "Requested remote branch does not resolve to a commit.",
                 "base": None, "base_candidates": []})

    if value.startswith("refs/"):
        record = base_record(repo, value, "requested")
        return ({"status": "resolved", "base": record, "base_candidates": []} if record else
                {"status": "error", "error": "Requested ref does not resolve to a commit.",
                 "base": None, "base_candidates": []})

    for remote in sorted(remotes, key=len, reverse=True):
        prefix = remote + "/"
        if value.startswith(prefix):
            record = base_record(repo, "refs/remotes/" + value, "requested")
            return ({"status": "resolved", "base": record, "base_candidates": []} if record else
                    {"status": "error", "error": "Requested remote branch does not resolve to a commit.",
                     "base": None, "base_candidates": []})

    candidates = all_candidates(repo, value)
    if len(candidates) == 1:
        candidates[0]["source"] = "requested"
        return {"status": "resolved", "base": candidates[0], "base_candidates": []}
    if len(candidates) > 1:
        return base_selection("Branch name matches multiple local or remote branches.", candidates)
    return {"status": "error", "error": "Requested branch does not resolve to a commit.",
            "base": None, "base_candidates": []}


def safe_regular_file(root, relative):
    path = os.path.join(root, relative)
    try:
        if not stat.S_ISREG(os.lstat(path).st_mode):
            return False
        current = root
        for component in relative.split(os.sep):
            current = os.path.join(current, component)
            if stat.S_ISLNK(os.lstat(current).st_mode):
                return False
        return os.path.commonpath((root, os.path.realpath(path))) == root
    except (FileNotFoundError, ValueError):
        return False


def template_candidates(root):
    candidates = [path for path in TEMPLATE_FILES if safe_regular_file(root, path)]
    for directory in TEMPLATE_DIRS:
        absolute = os.path.join(root, directory)
        try:
            entries = sorted(os.listdir(absolute))
        except FileNotFoundError:
            continue
        for entry in entries:
            relative = os.path.join(directory, entry)
            if entry.lower().endswith(".md") and safe_regular_file(root, relative):
                candidates.append(relative)
    return sorted(set(candidates))


def resolve_template(root, requested):
    candidates = template_candidates(root)
    if requested is not None:
        if requested in candidates:
            return {"status": "resolved", "path": requested, "candidates": [], "reason": None}
        return {"status": "error", "error": "Requested template is not a safe discovered template.",
                "path": None, "candidates": candidates, "reason": None}
    if len(candidates) == 1:
        return {"status": "resolved", "path": candidates[0], "candidates": [], "reason": None}
    if len(candidates) > 1:
        return {"status": "selection_required", "path": None, "candidates": candidates,
                "reason": "Multiple safe PR templates were found; select one template path."}
    return {"status": "none", "path": None, "candidates": [], "reason": None}


def resolve(repo, base, template):
    root = git(repo, "rev-parse", "--show-toplevel")
    head = branch_context(root)
    base_result = resolve_base(root, base, head)
    template_result = resolve_template(root, template)
    errors = [result["error"] for result in (base_result, template_result)
              if result.get("status") == "error"]
    selections = [result.get("reason") for result in (base_result, template_result)
                  if result.get("status") == "selection_required"]
    status = "error" if errors else "selection_required" if selections else "resolved"
    return {"status": status, "repository": root, "head": head,
            "base": base_result["base"], "base_candidates": base_result["base_candidates"],
            "template": template_result, "error": "; ".join(errors) if errors else None,
            "selection_reasons": selections}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=".")
    parser.add_argument("--template")
    parser.add_argument("base", nargs="?")
    args = parser.parse_args()
    try:
        print(json.dumps(resolve(args.repo, args.base, args.template), sort_keys=True))
    except GitError as error:
        print(json.dumps({"status": "error", "error": str(error)}))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
