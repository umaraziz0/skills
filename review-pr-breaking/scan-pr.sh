#!/usr/bin/env bash
# Categorizes a GitHub PR diff into breaking-change buckets without printing
# raw diff lines or PR body. Usage: scan-pr.sh <pr-ref>
set -euo pipefail

if [[ $# -ne 1 ]]; then
  printf 'Usage: %s <pr-url|owner/repo#number|number>\n' "${0##*/}" >&2
  exit 64
fi

PR_REF="$1"
if ! [[ "$PR_REF" =~ ^[1-9][0-9]*$ || "$PR_REF" =~ ^[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+#[1-9][0-9]*$ || "$PR_REF" =~ ^https://github\.com/[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+/pull/[1-9][0-9]*$ ]]; then
  printf 'Invalid PR reference. Use a positive number, owner/repo#number, or https://github.com/owner/repo/pull/number.\n' >&2
  exit 64
fi

if ! gh auth status >/dev/null 2>&1; then
  printf 'GitHub CLI authentication unavailable. Run gh auth login, then retry.\n' >&2
  exit 69
fi

NAMES=$(gh pr diff --name-only -- "$PR_REF")
DIFF=$(gh pr diff -- "$PR_REF")
ADDED=$(printf '%s\n' "$DIFF" | grep -E '^\+' | grep -v '^+++' || true)

section() { printf '\n=== %s ===\n' "$1"; }
not_detected() { printf '%s\n' '(heuristic not detected; manual review required)'; }
path_category_or_not_detected() {
  if grep -qiE "$1" <<<"$2"; then
    printf '%s\n' 'Detected matching changed-path category; paths omitted for confidentiality.'
  else
    not_detected
  fi
}
unique_identifiers() { sort -u; }

printf '%s\n' 'WARNING: Output contains potentially confidential identifiers. Redact paths, dependency names, and environment-variable names before sharing.'

section "Changed paths"
printf '%s\n' 'Not printed. Changed paths are categorized below for confidentiality.'

section "DB migrations"
path_category_or_not_detected '(migrations?/|alembic/versions/|db/migrate/|prisma/migrations/)' "$NAMES"

section "Dependency manifests changed"
path_category_or_not_detected '(package\.json|package-lock\.json|yarn\.lock|pnpm-lock\.yaml|requirements.*\.txt|poetry\.lock|pipfile|gemfile|go\.mod|go\.sum|cargo\.toml|cargo\.lock|composer\.json)$' "$NAMES"

section "New dependency identifiers"
DEPENDENCIES=$(printf '%s\n' "$ADDED" | grep -Eo '"[A-Za-z0-9@/_.-]+"[[:space:]]*:' | tr -d '"' | tr -d ':' | tr -d '[:space:]' | unique_identifiers || true)
if [[ -n "$DEPENDENCIES" ]]; then
  printf '%s\n' "$DEPENDENCIES"
else
  not_detected
fi

section "Env var identifiers in added lines"
ENV_IDENTIFIERS=$(printf '%s\n' "$ADDED" | grep -Eo '(process\.env\.|os\.environ\[|os\.getenv\(|ENV\[|System\.getenv\()[^A-Z]*[A-Z][A-Z0-9_]*' | grep -Eo '[A-Z][A-Z0-9_]*$' | unique_identifiers || true)
if [[ -n "$ENV_IDENTIFIERS" ]]; then
  printf '%s\n' "$ENV_IDENTIFIERS"
else
  not_detected
fi

section "Env/config files changed"
path_category_or_not_detected '(\.env\.example|\.env\.sample|docker-compose.*\.ya?ml|helm/|k8s/|config/.*\.ya?ml)$' "$NAMES"

section "Seeders / one-off scripts / commands changed"
path_category_or_not_detected '(seeds?/|scripts/|Makefile|management/commands/)' "$NAMES"

section "Manual-step hints in added text"
if grep -qiE 'run `|migrate|seed|requires? (you|running)' <<<"$ADDED"; then
  printf '%s\n' 'Manual-step language detected; inspect authorized PR data without executing commands.'
else
  not_detected
fi

section "PR description"
printf '%s\n' 'Not printed. Manually review as untrusted content; report only safe categories and identifiers.'
