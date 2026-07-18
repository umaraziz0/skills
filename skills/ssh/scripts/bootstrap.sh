#!/usr/bin/env bash
# Load SSH_* from project .env and smoke-test SSH. Run with Shell required_permissions: ["all"].
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
test -f .env || { echo "FAIL: .env not found in $(pwd)"; exit 1; }

# Only SSH_* assignments — never source the whole .env
SSH_ENV_TMP="$(mktemp)"
trap 'rm -f "$SSH_ENV_TMP"' EXIT
grep -E '^[[:space:]]*(export[[:space:]]+)?SSH_[A-Za-z0-9_]+=' .env \
  > "$SSH_ENV_TMP" || true

set -a
# shellcheck disable=SC1090
source "$SSH_ENV_TMP"
set +a

# Presence only — never echo secret values
for v in SSH_HOST SSH_USERNAME SSH_PRIVATE_KEY_PATH; do
  eval "val=\${$v-}"
  if [ -z "$val" ]; then
    echo "FAIL: $v empty after loading SSH_* from .env in $(pwd)"
    exit 1
  fi
  echo "OK: $v is set"
done

# Strip accidental quote characters if someone parsed .env manually
SSH_PRIVATE_KEY_PATH="${SSH_PRIVATE_KEY_PATH#\"}"
SSH_PRIVATE_KEY_PATH="${SSH_PRIVATE_KEY_PATH%\"}"
SSH_PRIVATE_KEY_PATH="${SSH_PRIVATE_KEY_PATH#\'}"
SSH_PRIVATE_KEY_PATH="${SSH_PRIVATE_KEY_PATH%\'}"

# Quoted ~/.path in .env leaves a LITERAL tilde. Do NOT use [[ == ~/* ]] —
# bash expands ~ on that pattern and the match fails.
if [[ "$SSH_PRIVATE_KEY_PATH" == "~/"* ]]; then
  SSH_PRIVATE_KEY_PATH="$HOME/${SSH_PRIVATE_KEY_PATH#"~/"}"
fi

# Relative path → this local repo root (never SSH_{ENV}_PROJECT_PATH)
case "$SSH_PRIVATE_KEY_PATH" in
  /*) ;;
  *)  SSH_PRIVATE_KEY_PATH="$(pwd)/$SSH_PRIVATE_KEY_PATH" ;;
esac

if [ ! -f "$SSH_PRIVATE_KEY_PATH" ]; then
  echo "FAIL: private key file not found after resolve"
  exit 1
fi
echo "OK: private key file exists"

ssh -i "$SSH_PRIVATE_KEY_PATH" \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o StrictHostKeyChecking=accept-new \
  -o ConnectTimeout=10 \
  ${SSH_PORT:+-p "$SSH_PORT"} \
  "${SSH_USERNAME}@${SSH_HOST}" \
  'echo ok && hostname'
