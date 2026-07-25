# Flow mode

Read this file completely after the router selects Flow, then execute Flow
only. Do not read or execute Diff instructions.

## Roots and snapshot

Require one or more existing regular files. Resolve relative paths against the
repository root. Reject missing paths and paths whose canonical target is
outside the repository, including symlinks escaping it. No fixed point is
needed.

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
- Roots: <files>
- Traced first-party files/entry points: <files and entry points>
- External boundaries/contracts: <boundaries and relied-on contracts>
- Blind spots: <unresolved dynamic paths or None.>
```
