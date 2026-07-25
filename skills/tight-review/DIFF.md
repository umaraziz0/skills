# Diff mode

Read this file completely after the router selects Diff, then execute only the
selected subtype. Do not read or execute Flow instructions.

## Merge-base subtype (default)

Require a fixed point (commit, tag, or branch); do not infer it from branch
name, upstream, or default branch. Resolve the ref once to `FIXED_POINT` and
use that SHA throughout. Validate the ref and require a non-empty three-dot
diff:

```sh
FIXED_POINT="$(git rev-parse --verify '<ref>^{commit}')"
HEAD_COMMIT="$(git rev-parse --verify 'HEAD^{commit}')"
git diff --quiet "$FIXED_POINT...$HEAD_COMMIT" --
```

If ref validation fails, ask for a corrected ref. A zero exit from
`git diff --quiet` means stop: empty review range. Review merge-base diff
`FIXED_POINT...HEAD_COMMIT`; never substitute a two-dot range. Capture commits
before lane work:

```sh
git log --reverse --format='%H%n%s%n%b%n' "$FIXED_POINT..$HEAD_COMMIT"
git diff --name-status "$FIXED_POINT...$HEAD_COMMIT" --
git status --short
```

Read changed hunks and surrounding context as needed. Findings target changed
lines. Uncommitted work is outside this subtype. Use read-only commands only.

## Worktree subtype

Compare current working-tree content to `HEAD`. For tracked files use
`git diff HEAD --`, combining staged and unstaged net changes without
double-counting. Capture status and names with read-only commands:

```sh
git status --short --untracked-files=all
git diff --name-status HEAD --
git diff HEAD --
git ls-files --others --exclude-standard -z
```

Include every path from `git ls-files --others --exclude-standard` that is a
regular, non-ignored file; treat each full untracked file as added content.
Require at least one staged, unstaged, or untracked change. If tracked net
diff and untracked-file list are both empty, stop: empty scope.

For every reviewed path, reject or record unreadable, escaping-symlink, binary,
or unsupported paths as explicit blind spots; never silently claim coverage.
Before findings, write `Blind spots: <path> — <reason>` for each such path;
omit that line when none exist. Findings target added or modified current-
worktree lines. For deleted-line-only issues, point to a precise diff location
and state clearly what the deletion breaks. Never stage or mutate.

## Exact-range subtype

Resolve `<base>` and `<head>` once to commit SHAs; `HEAD` is valid and means the
latest commit:

```sh
BASE_COMMIT="$(git rev-parse --verify '<base>^{commit}')"
HEAD_COMMIT="$(git rev-parse --verify '<head>^{commit}')"
git merge-base --is-ancestor "$BASE_COMMIT" "$HEAD_COMMIT"
git diff --quiet "$BASE_COMMIT..$HEAD_COMMIT" --
```

If either ref is invalid or base is not an ancestor of head, ask for corrected
refs. Review aggregate net endpoint diff `BASE_COMMIT..HEAD_COMMIT`, not each
commit independently. The base tree is excluded; pass `<base>^` when the base
commit itself must be included. A zero exit from `git diff --quiet` means stop:
empty range. Capture commits and changed files:

```sh
git log --reverse --format='%H%n%s%n%b%n' "$BASE_COMMIT..$HEAD_COMMIT"
git diff --name-status "$BASE_COMMIT..$HEAD_COMMIT" --
```

Uncommitted changes are excluded. Findings target changed lines in the endpoint
diff. Use read-only commands only.
