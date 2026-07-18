# Context resolution contract

No-base invocation: `python3 resolve_context.py --repo PATH`. Explicit-base invocation: `python3 resolve_context.py --repo PATH "BASE"`. `PATH` may be `"$PWD"`. After user chooses one returned template candidate, add `--template "RELATIVE_PATH"` before the base argument. Resolver uses only local, read-only Git commands and prints one JSON object.

## JSON result

Every successful invocation returns `repository`, `head`, `base`, `base_candidates`, `template`, `selection_reasons`, `error`, and `status`.

- `head` is `{commit, branch, detached}`.
- Resolved `base` is `{ref, commit, source}` and adds `{remote, branch}` only for remote-tracking refs. `base_candidates` is empty then.
- `template` is `{status, path, candidates, reason}`. Status is `resolved`, `none`, `selection_required`, or `error`. Its `reason` is non-null whenever template status is `selection_required`.
- Top-level `status` is `resolved` only when base and template are complete; `selection_required` when either needs user selection; `error` when either is invalid. `selection_reasons` contains every non-null pending-selection reason. `error` is otherwise `null`.

## Base rules

- Requested `remote counterpart`, `remote tracking`, or `upstream`: current branch upstream.
- Bare remote name: current upstream only when it uses that remote; otherwise selection among that remote's known branches.
- `<remote> <branch>` and `<remote>/<branch>`: matching remote-tracking ref for any known remote.
- Full `refs/...`: exact validated commit ref.
- Simple branch: inspect matching local and every remote-tracking branch. Zero matches is error; more than one requires selection; one resolves.
- No requested base: identify current branch's remote-tracking upstream, then resolve only that remote's symbolic `refs/remotes/<remote>/HEAD`. Its valid target resolves as `base.ref`. Missing upstream or symbolic remote HEAD requires selection. No feature upstream branch, remote name, or branch name is assumed.

Resolved base JSON contains immutable `ref`, commit OID, source, and remote/branch for remote-tracking refs. `selection_required` contains reason and candidates. Call resolver again after user selection or optional fetch; never cache its result across plans.

## Template rules

Safe candidates include standalone `.github/pull_request_template.md`, `PULL_REQUEST_TEMPLATE.md`, `pull_request_template.md`, `docs/pull_request_template.md`, plus immediate Markdown files in `.github/PULL_REQUEST_TEMPLATE/`, `PULL_REQUEST_TEMPLATE/`, and `docs/PULL_REQUEST_TEMPLATE/`. Candidates are sorted by relative path. One resolves; none returns `template.status: none`; multiple require explicit `--template` selection. Symlinks, non-regular files, and files resolving outside repository are ignored. Caller reads only resolved `template.path`.

Use only resolved `base.ref` for `git merge-base`, log, and diff commands. Never substitute raw requested base text after resolution.

## Safety

Resolver does not fetch, modify refs, checkout, or write files. User-controlled refs are passed after Git `--end-of-options` and must resolve to commits.
