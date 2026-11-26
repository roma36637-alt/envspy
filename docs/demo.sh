#!/usr/bin/env bash
# envspy terminal demo.
#
# Play it:   bash docs/demo.sh
# Record it: asciinema rec demo.cast -c "bash docs/demo.sh"   # then upload demo.cast
#
# The script writes its own throwaway .env file so the --check step always fails
# on a fresh checkout (that is the point of the demo).
set -euo pipefail
cd "$(dirname "$0")/.."

# Pick a Python that actually runs. On Windows the Microsoft Store ships a
# `python3` "app execution alias" that only prints a stub message and exits 49.
pick_python() {
  local c
  for c in python3 python py; do
    if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys' >/dev/null 2>&1; then
      # Return the *name*, not the absolute path, so the report title reads
      # `python examples/demo.py` instead of C:/.../python.exe.
      printf '%s' "$c"
      return 0
    fi
  done
  echo "bash: no working Python interpreter found (tried python3, python, py)" >&2
  return 1
}
PY=$(pick_python)

say() {
  printf '\n\033[1;36m$ %s\033[0m\n' "$*"
  sleep 0.5
}

say "envspy -- python examples/demo.py"
"$PY" -m envspy -- "$PY" examples/demo.py || true

if command -v node >/dev/null 2>&1; then
  say "envspy -- node examples/demo.js"
  "$PY" -m envspy -- node examples/demo.js || true
fi

TMP=.env.example.demo
printf 'DATABASE_URL=\nDEBUG=\nPORT=\n' > "$TMP"
say "envspy --check $TMP -- python examples/demo.py   # fails CI, exits 1"
"$PY" -m envspy --check "$TMP" -- "$PY" examples/demo.py || echo "exit=$?"
rm -f "$TMP"