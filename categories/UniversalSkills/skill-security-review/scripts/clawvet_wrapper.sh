#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "usage: clawvet_wrapper.sh <target-path> [extra args...]" >&2
  exit 2
fi

TARGET="$1"
shift || true

if command -v clawvet >/dev/null 2>&1; then
  CMD=(clawvet scan "$TARGET" "$@")
else
  CMD=(npx --yes clawvet@0.6.3 scan "$TARGET" "$@")
fi

"${CMD[@]}"
