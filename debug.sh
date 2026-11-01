#!/usr/bin/env bash
# Run the FastAPI backend under debugpy for the "Attach to FastAPI (debug.sh)"
# configuration in .vscode/launch.json, then the Streamlit frontend once the backend is up.
# Usage: ./debug.sh
# The backend starts once the debugger attaches, so breakpoints in startup code hit.
# Auto-reload is off because it runs the app in a subprocess debugpy isn't attached to.
# Ctrl+C stops both. If either one exits, the other is stopped too.
# Ports can be overridden with BACKEND_PORT, FRONTEND_PORT and DEBUG_PORT
# (keep DEBUG_PORT in sync with launch.json).

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-8501}"
DEBUG_PORT="${DEBUG_PORT:-5678}"

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

echo "Waiting for debugger on 127.0.0.1:$DEBUG_PORT..."

# Frozen modules can make debugpy miss breakpoints in the standard library
uv run --with debugpy python -Xfrozen_modules=off -m debugpy \
  --listen "127.0.0.1:$DEBUG_PORT" \
  --wait-for-client \
  -m fastapi dev src/omnichat_ai/backend/qa-backend.py --no-reload --port "$BACKEND_PORT" &
backend_pid=$!

# No timeout: this also waits for the debugger, which can take as long as it takes to attach
until curl -sf -o /dev/null "http://127.0.0.1:$BACKEND_PORT/openapi.json"; do
  if ! kill -0 "$backend_pid" 2>/dev/null; then
    echo "Backend stopped before it was ready."
    exit 1
  fi
  sleep 1
done

OMNICHAT_BACKEND_URL="http://localhost:$BACKEND_PORT" \
  uv run streamlit run src/omnichat_ai/frontend/app.py --server.port "$FRONTEND_PORT" &
frontend_pid=$!

# Poll because macOS ships bash 3.2, which has no `wait -n`
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done

echo "A server stopped; shutting down."
exit 1
