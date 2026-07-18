#!/usr/bin/env bash
# Compatibility entrypoint. Scanner implementation uses only Python stdlib.
set -euo pipefail
exec python3 "$(dirname "${BASH_SOURCE[0]}")/scan_pr.py" "$@"
