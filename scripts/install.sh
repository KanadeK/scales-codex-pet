#!/usr/bin/env sh
set -eu

project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

if command -v python3 >/dev/null 2>&1; then
  python_bin=python3
elif command -v python >/dev/null 2>&1; then
  python_bin=python
else
  echo "Python 3.11 or newer is required." >&2
  exit 1
fi

"$python_bin" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' || {
  echo "Python 3.11 or newer is required." >&2
  exit 1
}

"$python_bin" -m pip install "$project_root"
"$python_bin" -m scales_pet validate "$project_root/pet" --target desktop --strict

if [ "${CODEX_HOME:-}" ]; then
  "$python_bin" -m scales_pet install \
    --source "$project_root/pet" \
    --codex-home "$CODEX_HOME" \
    "$@"
else
  "$python_bin" -m scales_pet install --source "$project_root/pet" "$@"
fi

echo "Scales is ready. Refresh Settings > Pets in Codex."
