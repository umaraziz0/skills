# Scanner configuration

Optional configuration is `.github/pr-breaking.json` at verified target-checkout root. Scanner resolves PR target through `gh`, then compares target host/repository with URLs from every configured current-checkout remote. It auto-loads configuration only when exactly one remote matches. No explicit config-path option exists.

Run skill-directory wrapper from intended target checkout:

```sh
<skill-dir>/scan-pr.sh owner/repo#123
```

For URL, `owner/repo#number`, or bare-number scans, an unrelated checkout never contributes configuration; defaults apply. Multiple matching remotes are ambiguous and cause nonzero exit. Scanner never downloads configuration through `gh`, from PR body, or from PR diff.

```json
{
  "detectors": {
    "db_migrations": {"paths": ["database/changes/**"]}
  }
}
```

Built-in path-detector keys: `db_migrations`, `dependency_manifests`, `env_config`, `scripts`. `paths` extends registry defaults. Configuration cannot disable, replace, or otherwise reduce any detector coverage. `dependency_manifests.paths` also extends manifest patches eligible for dependency-identifier extraction.

## Valid configuration

Document must contain exactly top-level `detectors` object. Each detector entry must use known key and contain exactly `paths` array. Every path must be relative string of 1–200 characters, contain no `..` path segment or null byte, and not start with `/`. Paths are glob patterns, not regexes.

## Invalid configuration

When verified checkout contains configuration, malformed JSON, unreadable or oversized (>32,768 bytes) file, unknown keys, extra fields, non-array paths, or invalid path entries cause scanner error and nonzero exit. Missing configuration, or configuration in unverified/unrelated checkout, is ignored because defaults apply. Configuration cannot add commands, regexes, output templates, or detector code.
