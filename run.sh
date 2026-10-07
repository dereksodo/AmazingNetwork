#!/usr/bin/env bash
# Start the Connect proof of concept locally (macOS / Linux).
# First run: creates backend/.venv and installs the Python packages.
# Later runs: reuses the venv and only reinstalls if the requirements changed.
#   ./run.sh        start backend (port 8000) and frontend (port 5173)
#   ./run.sh test   install, then run the test suite
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$ROOT/backend/.venv"
STAMP="$VENV/.requirements-installed"

PYTHON="${PYTHON:-python3}"
if ! "$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
  echo "Python 3.11 or newer is required (found: $("$PYTHON" --version 2>&1))." >&2
  exit 1
fi

if [ ! -x "$VENV/bin/python" ]; then
  echo "Creating virtual environment in backend/.venv ..."
  "$PYTHON" -m venv "$VENV"
fi

REQS="$ROOT/backend/requirements.txt $ROOT/backend/requirements-dev.txt"
if [ ! -f "$STAMP" ] || [ -n "$(find $REQS -newer "$STAMP")" ]; then
  echo "Installing Python packages ..."
  "$VENV/bin/pip" install --quiet --upgrade pip
  "$VENV/bin/pip" install --quiet -r "$ROOT/backend/requirements-dev.txt"
  touch "$STAMP"
fi

cd "$ROOT/backend"

if [ "${1:-}" = "test" ]; then
  exec "$VENV/bin/pytest"
fi

"$VENV/bin/python" -m http.server 5173 --directory "$ROOT/frontend" >/dev/null 2>&1 &
FRONTEND_PID=$!
trap 'kill $FRONTEND_PID 2>/dev/null' EXIT

echo
echo "  Frontend:  http://localhost:5173"
echo "  API docs:  http://127.0.0.1:8000/docs"
echo "  Press Ctrl+C to stop both."
echo
"$VENV/bin/uvicorn" app.main:app --port 8000
