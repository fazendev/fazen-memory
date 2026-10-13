#!/usr/bin/env bash
# Runs a Fazen Memory hook (on_prompt.py / on_stop.py) with the first Python 3 that really starts.
# `python3`, `python` and `py` can each be a broken stub on Windows (Store alias, launcher pointing
# to an uninstalled version), so every candidate is tried before it is used. No Python: exit 0 quietly.
script="$(dirname "$0")/$1"
for py in python3 python py "$HOME"/AppData/Local/Programs/Python/Python3*/python.exe "/c/Program Files"/Python3*/python.exe; do
  # </dev/null: the probe must not eat the hook's JSON on stdin
  if "$py" -c 'import sys; sys.exit(sys.version_info < (3, 8))' </dev/null >/dev/null 2>&1; then
    exec "$py" "$script"
  fi
done
exit 0
