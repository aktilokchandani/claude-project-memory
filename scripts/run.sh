#!/bin/sh
# Finds a working Python 3 on Windows, macOS or Linux and runs one of the plugin scripts.
# Usage: sh run.sh <script name without .py> [args...]
here=$(cd "$(dirname "$0")" && pwd)
name=$1
shift
for py in python3 python py; do
  if command -v "$py" >/dev/null 2>&1 && "$py" -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" </dev/null >/dev/null 2>&1; then
    exec "$py" "$here/$name.py" "$@"
  fi
done
echo "project-memory: Python 3.8+ not found. Install Python and make sure 'python3' or 'python' is on PATH." >&2
exit 0
