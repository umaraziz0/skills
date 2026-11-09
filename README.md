# Skills

Various project-agnostic engineering agent skills.

## Table of contents

- [Install with skills.sh](#install-with-skillssh)
- [Available skills](#available-skills)
  - [Cleanup tests](#cleanup-tests)
  - [File PR](#file-pr)
  - [Babysit PR](#babysit-pr)
  - [Review PR breaking changes](#review-pr-breaking-changes)
  - [Tight review](#tight-review)
  - [Update docs](#update-docs)
  - [Verify implementation](#verify-implementation)
  - [Implement with verify](#implement-with-verify)

## Install with skills.sh

Install all skills from this repository:

```sh
npx skills add umaraziz0/skills
```

Install to specific agents only (e.g opencode):

```sh
npx skills add umaraziz0/skills -a opencode
```

List available skills before installing:

```sh
npx skills add umaraziz0/skills --list
```

## Available skills

### Cleanup tests

Evidence-driven test cleanup with an exhaustive whole-suite audit by default.
Always audits first, then requires confirmation before safe test-only edits;
explicit narrowed forms support `files`, `diff`, and `feature` scopes. Reviews
tautological, low-value, duplicate, snapshot, flaky, slow, and unreadable tests
without changing production code.

```sh
/cleanup-tests
/cleanup-tests files tests/auth_test.rb
/cleanup-tests diff HEAD~1
/cleanup-tests feature authentication
```

### File PR

Publish the current branch’s committed history (leave the starting dirty tree
alone), open or reuse a PR to the default branch, fill
`docs/pull_request_template.md` when present (and write the body with
`technical-writing` when that skill is installed).

```sh
/file-pr
```

### Babysit PR

Watch CI for the current branch’s existing PR. Diagnose failing checks and
apply up to three scoped fix-and-push attempts until required checks are green.
Leave starting dirty paths uncommitted.

```sh
/babysit-pr
```

### Review PR breaking changes

Post-merge ops checklist for a user-provided GitHub PR (URL, `#n`, or
`owner/repo#n`). Flags migrations, dependency bumps, env/key changes,
seeders, and queue-worker restarts (e.g. Laravel Jobs). Deploy cheat sheet
only — does not merge, approve, or run migrate/seed/install.

```sh
/review-pr-breaking <PR>
```

### Tight review

Read-only implementation review. Starts from a commit, explicit file roots, or
a feature/domain, then traces relevant current working-tree behavior. Checks
correctness, spec/ticket compliance, documented repository standards, and
unnecessary complexity in separate lanes; does not mutate, approve, or request
changes. A lean combination of:

- [/ponytail-review](https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail-review) - for tight coding principles
- [/code-review](https://github.com/mattpocock/skills/tree/main/skills/engineering/code-review) - for spec and style adherence
- [/caveman-review](https://github.com/JuliusBrussee/caveman/tree/main/skills/caveman-review) - for simplified code review output

```sh
/tight-review HEAD
/tight-review files src/auth.ts src/routes.ts
/tight-review authentication
```

- Commit ref: use files changed by that commit as discovery seeds, then review
  their current implementation. The commit is not a diff base or historical
  snapshot.
- Files: trace current implementation from explicit roots.
- Feature/domain: discover a bounded implementation scope, then trace it.

### Update docs

Reconcile all tracked Markdown and MDX documentation with package manifests,
lockfiles, configuration, and current implementation. The skill updates proven
drift with `technical-writing` when that skill is installed, and leaves code and
dependency files unchanged. It reports ambiguous claims without guessing.

```sh
/update-docs
```

### Verify implementation

Verify a change by exercising it rather than reading it. The skill builds a
scenario from every spec behaviour and runs the repository's own checks. It
then drives the real app, endpoint, CLI, migration, or mail flow, fixing minor
defects and asking before major ones. Last, it restores any local data it
changed and reports a scenario matrix. Agents can also run it on their own after
implementing.

```sh
/verify-implementation
/verify-implementation HEAD~2..HEAD
/verify-implementation booking form error states
```

### Implement with verify

Matt Pocock's `/implement` skill with [`/verify-implementation`](#verify-implementation) added.
Calls `tdd` and `code-review` skills; install them alongside this one.

```sh
/implement-with-verify
/implement-with-verify #123
/implement-with-verify docs/specs/booking-form.md
```
