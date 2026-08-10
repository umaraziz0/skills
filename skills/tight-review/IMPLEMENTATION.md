# Implementation trace

## Input scope

Implementation review accepts explicit file roots, descriptive implementation
scope, or a commit discovery seed.

### Explicit roots

Require one or more existing regular files. Resolve relative paths against the
repository root. Reject missing paths and paths whose canonical target is
outside the repository, including symlinks escaping it.

### Descriptive scope

Treat the concept as a scope query, not as a path or permission to search the
whole repository. Discover likely first-party entry/root files from current
repository evidence only: local docs and README guidance, package manifests,
route/command/entrypoint declarations, and source names or symbols that
directly identify the concept. Prefer exact concept evidence and public
entrypoints, then the smallest evidence-backed root set that covers the named
implementation. Exclude unrelated matches, generated/vendor trees, and
whole-directory expansion.

Proceed only when evidence supports one unique or clearly reasonable bounded
implementation scope. State the interpreted concept and selected roots. If no
reasonable scope can be inferred, or multiple scopes are equally plausible, ask
one focused clarification naming the candidate scopes; never silently widen
scope.

### Commit seed

Use commit input only to discover candidate roots. Resolve exactly one ref once,
read-only; `HEAD` is valid:

```sh
COMMIT="$(git rev-parse --verify '<commit-ref>^{commit}')"
```

Obtain paths changed by that commit itself, including root commits:

```sh
git show --root --format= --name-status --find-renames "$COMMIT" --
```

Use existing regular first-party files from that changed-path set as candidate
roots. Deleted paths remain discovery evidence but cannot become roots. Renamed
paths contribute their old and new paths for discovery, but only an existing
current path can become a root. Apply repository-root, regular-file, and
escaping-symlink checks from Explicit roots. Exclude generated, vendor,
dependency, and other non-first-party paths using repository evidence. The
commit is not a comparison base and does not select a historical snapshot; read
every root and traced file from the current working-tree snapshot.

If changed files span multiple unrelated implementations, or no bounded
implementation trace can be inferred, ask one focused clarification naming the
candidate implementations or missing scope. Do not silently choose one
implementation or broaden roots beyond the changed-path evidence. After roots
are selected, trace only the bounded implementation reachable from them.

## Roots and snapshot

Read the current working-tree snapshot, including unchanged and uncommitted
content, without mutation. Listed files are roots, not hard boundaries. A
commit seed never causes checkout, reset, historical reads, or repository
mutation.

## Trace

Identify relevant public or external entry points and routes/callers as needed.
Trace reachable first-party calls through validation, authorization/trust
boundaries, branches, state changes and side effects, errors, and
outputs/responses. Stop at framework/vendor boundaries and record relied-on
contracts. Avoid unrelated code and detect cycles.

State unresolved dynamic dispatch, event, or reflection paths as blind spots.
Findings may target any in-scope traced line.

## Implementation scope output

Before the four shared finding sections, output:

```markdown
## Scope
- Requested scope: <commit ref, explicit roots, or descriptive concept>
- Roots: <files>
- Traced first-party files/entry points: <files and entry points>
- External boundaries/contracts: <boundaries and relied-on contracts>
- Blind spots: <unresolved dynamic paths or None.>
```
