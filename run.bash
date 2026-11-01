#!/usr/bin/env bash
# Run the FastAPI backend and the Streamlit frontend together.
# Usage: ./run.bash
# Ctrl+C stops both. If either one exits, the other is stopped too.
# Ports can be overridden with BACKEND_PORT and FRONTEND_PORT.

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8501}"

# Run from the project root so paths and .env resolve from any directory
cd "$(dirname "${BASH_SOURCE[0]}")"

# Make sure uv is installed
if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv is not installed."
  exit 1
fi

cleanup() {
  trap - EXIT INT TERM
  kill "${backend_pid:-}" "${frontend_pid:-}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

uv run fastapi dev src/omnichat_ai/backend/qa-backend.py --port "$BACKEND_PORT" &
backend_pid=$!

OMNICHAT_BACKEND_URL="http://localhost:$BACKEND_PORT" \
  uv run streamlit run src/omnichat_ai/frontend/app.py --server.port "$FRONTEND_PORT" &
frontend_pid=$!

# Poll because macOS ships bash 3.2, which has no `wait -n`
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

echo "A server stopped; shutting down."
exit 1
