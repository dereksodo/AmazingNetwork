#!/usr/bin/env bash
# Install and start Connect locally (macOS / Linux).
#   ./run.sh        start the backend (port 8000) and the frontend (port 5173)
#   ./run.sh seed   replace all data with the demonstration data
#   ./run.sh test   run the backend tests
#   ./run.sh lint   check formatting and linting of backend and frontend
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${PYTHON:-python3}"
BIN="$ROOT/backend/.venv/bin"

[ -d "$ROOT/backend/.venv" ] || "$PYTHON" -m venv "$ROOT/backend/.venv"
"$BIN/pip" install --quiet --disable-pip-version-check -r "$ROOT/backend/requirements-dev.txt"
[ -f "$ROOT/.env" ] || cp "$ROOT/.env.example" "$ROOT/.env"

cd "$ROOT/backend"
set -a
. "$ROOT/.env"
set +a

case "${1:-start}" in
  seed)
    exec "$BIN/python" -m scripts.seed
    ;;
  test)
    exec "$BIN/pytest"
    ;;
  lint)
    npm ci --silent --prefix "$ROOT/frontend"
    "$BIN/ruff" format --check .
    "$BIN/ruff" check .
    npm run format:check --prefix "$ROOT/frontend"
    npm run lint --prefix "$ROOT/frontend"
    ;;
  start)
    [ -f connect.db ] || "$BIN/python" -m scripts.seed
    npm ci --silent --prefix "$ROOT/frontend"
    "$BIN/uvicorn" app.main:app --port 8000 &
    trap 'kill $!' EXIT
    echo "Open http://localhost:5173  (API documentation: http://127.0.0.1:8000/docs)"
    npm run dev --prefix "$ROOT/frontend"
    ;;
esac
