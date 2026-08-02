# Flow mode

## Input scope

Flow accepts either explicit file roots or descriptive flow scope.

### Explicit roots

Require one or more existing regular files. Resolve relative paths against the
repository root. Reject missing paths and paths whose canonical target is
outside the repository, including symlinks escaping it. No fixed point is
needed.

### Descriptive scope

Treat the concept as a scope query, not as a path or permission to search the
whole repository. Discover likely first-party entry/root files from current
repository evidence only: local docs and README guidance, package manifests,
route/command/entrypoint declarations, and source names or symbols that
directly identify the concept. Prefer exact concept evidence and public
entrypoints, then the smallest evidence-backed root set that covers the named
flow. Exclude unrelated matches, generated/vendor trees, and whole-directory
expansion.

Proceed only when evidence supports one unique or clearly reasonable bounded
scope. State the interpreted concept and selected roots. If no reasonable
scope can be inferred, or multiple scopes are equally plausible, ask one
focused clarification naming the candidate scopes; never silently widen scope.

## Roots and snapshot

Read the current working-tree snapshot, including unchanged and uncommitted
content, without mutation. Listed files are roots, not hard boundaries.

## Trace

Identify relevant public or external entry points and routes/callers as needed.
Trace reachable first-party calls through validation, authorization/trust
boundaries, branches, state changes and side effects, errors, and
outputs/responses. Stop at framework/vendor boundaries and record relied-on
contracts. Avoid unrelated code and detect cycles.

State unresolved dynamic dispatch, event, or reflection paths as blind spots.
Findings may target any in-scope traced line, changed or unchanged.

## Flow scope output

Before the four shared finding sections, output:

```markdown
## Scope
- Requested scope: <explicit roots or descriptive concept>
- Roots: <files>
- Traced first-party files/entry points: <files and entry points>
- External boundaries/contracts: <boundaries and relied-on contracts>
- Blind spots: <unresolved dynamic paths or None.>
```
