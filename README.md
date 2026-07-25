# Skills

Various project-agnostic engineering agent skills.

## Table of contents

- [Install with skills.sh](#install-with-skillssh)
- [Available skills](#available-skills)
  - [Generate PR description](#generate-pr-description)
  - [Review PR breaking changes](#review-pr-breaking-changes)
  - [Tight review](#tight-review)
  - [SSH](#ssh)

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

### Generate PR description

Paste-ready PR description from unpushed commits on the current branch
(`@{u}..HEAD`). Uses `docs/pull_request_description.md` when present;
otherwise Summary + Test plan. Does not create, edit, push, or open a PR.

```sh
/generate-pr-description
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

Read-only review with Diff mode by default and explicit Flow mode. Checks
correctness, spec/ticket compliance, documented repository standards, and
unnecessary complexity in separate lanes; does not mutate, approve, or request
changes. A lean combination of:

- [/ponytail-review](https://github.com/DietrichGebert/ponytail/tree/main/skills/ponytail-review) - for tight coding principles
- [/code-review](https://github.com/mattpocock/skills/tree/main/skills/engineering/code-review) - for spec and style adherence
- [/caveman-review](https://github.com/JuliusBrussee/caveman/tree/main/skills/caveman-review) - for simplified code review output

```sh
/tight-review <fixed-point>
/tight-review diff <fixed-point>
/tight-review flow src/auth.ts src/routes.ts
```

### SSH

Thin SSH wrapper. Ask once per session, then load **only `SSH_*` lines** from
project `.env` (`SSH_HOST`, `SSH_USERNAME`, `SSH_PRIVATE_KEY_PATH`) — never
source the whole file. Run remote commands, browse the filesystem, and debug
the host. After a successful connect, optional `SSH_{ENV}_PROJECT_PATH` scopes
work via `environment production` (etc.); paths are relative to the SSH user's
home unless absolute. Do not pass the env on `/ssh` itself (e.g. not
`/ssh preview`). Destructive commands require explicit confirmation before run.

```sh
/ssh
environment production
```
