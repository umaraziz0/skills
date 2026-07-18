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

`generate-pr-description` creates evidence-based, paste-ready PR descriptions from committed changes on current branch. It resolves base branch and optional template, then reports summary, changes, and test plan. It never creates, edits, pushes, or opens a PR.

**Setup:** Run from target Git repository. Requires Python 3 and Git. No additional configuration; optional repository PR template is detected during use.

### Review PR breaking changes

`review-pr-breaking` reviews GitHub or GitHub Enterprise pull requests for migrations, dependency changes, environment changes, and manual deployment steps before merge or deploy.

**Setup:** Run from target repository checkout. Requires Bash, Python 3, GitHub CLI (`gh`), and access to PR. Optional extension-only path configuration is available in [`skills/review-pr-breaking/references/configuration.md`](skills/review-pr-breaking/references/configuration.md); built-in detectors remain enabled.

### SSH

`ssh` safely selects configured SSH deployment target and runs only profile-approved operations. It binds target selection to endpoint, folder, and host-key identity; it does not open interactive shell or execute arbitrary remote commands.

**Setup:** Run from local Git project with Python 3, Git, OpenSSH client, SSH key/configuration, and remote POSIX shell. Add untracked, ignored, owner-only `.ssh-skill.json` at project root:

```json
{
  "targets": {
    "production": {
      "host": "production-app",
      "folder": "/var/www/app",
      "profile": "laravel"
    }
  }
}
```

Set restrictive permissions and ensure Git ignores config:

```sh
chmod 600 .ssh-skill.json
```

See [`skills/ssh/references/setup.md`](skills/ssh/references/setup.md) for full schema, legacy `.env` support, SSH client configuration, and host-key verification.
