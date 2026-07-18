# Skills

Various project-agnostic engineering agent skills.

## Table of contents

- [Install with skills.sh](#install-with-skillssh)
- [Available skills](#available-skills)
  - [Generate PR description](#generate-pr-description)
  - [Review PR breaking changes](#review-pr-breaking-changes)
  - [SSH](#ssh)

## Install with skills.sh

Install all skills from this repository:

```sh
npx skills add umaraziz0/skills
```

List available skills before installing:

```sh
npx skills add umaraziz0/skills --list
```

Install from local checkout:

```sh
git clone https://github.com/umaraziz0/skills.git
cd skills
npx skills add .
```

List local skills without installing:

```sh
npx skills add . --list
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

### SSH

Thin SSH wrapper using project `.env` (`SSH_HOST`, `SSH_USERNAME`,
`SSH_PRIVATE_KEY_PATH`). Run remote commands, browse the filesystem, and
debug the host. Destructive commands require explicit confirmation before
run.

```sh
/ssh
```
