#!/usr/bin/env bash
# Run the FastAPI backend under debugpy for the "Attach to FastAPI (debug.sh)"
# configuration in .vscode/launch.json.
# Usage: ./debug.sh
# The server starts once the debugger attaches, so breakpoints in startup code hit.
# Auto-reload is off because it runs the app in a subprocess debugpy isn't attached to.
# Ports can be overridden with BACKEND_PORT and DEBUG_PORT (keep DEBUG_PORT in sync with launch.json).

set -euo pipefail

BACKEND_PORT="${BACKEND_PORT:-8000}"
DEBUG_PORT="${DEBUG_PORT:-5678}"

# Run from the project root so paths and .env resolve from any directory
cd "$(dirname "${BASH_SOURCE[0]}")"

# Make sure uv is installed
if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv is not installed."
  exit 1
fi

echo "Waiting for debugger on 127.0.0.1:$DEBUG_PORT..."

# Frozen modules can make debugpy miss breakpoints in the standard library
exec uv run --with debugpy python -Xfrozen_modules=off -m debugpy \
  --listen "127.0.0.1:$DEBUG_PORT" \
  --wait-for-client \
  -m fastapi dev src/omnichat_ai/backend/qa-backend.py --no-reload --port "$BACKEND_PORT"
