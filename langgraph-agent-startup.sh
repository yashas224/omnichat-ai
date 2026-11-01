#!/usr/bin/env bash
# Initialize a uv project and install dependencies.
# Usage: ./setup.sh [project-name]
#   With a name, creates a new folder for the project.
#   Without one, initializes the current directory.

set -euo pipefail

# Make sure uv is installed
if ! command -v uv >/dev/null 2>&1; then
  echo "Error: uv is not installed."
  exit 1
fi

# Initialize the project
if [[ $# -ge 1 ]]; then
  uv init "$1"
  cd "$1"
else
  uv init
fi

# Add dependencies (fastapi[standard] is quoted so the shell doesn't treat the brackets as a glob)
uv add \
  black \
  dotenv \
  "fastapi[standard]" \
  isort \
  langchain-core \
  langchain-openai \
  langchain-tavily \
  streamlit

echo "Done. Project set up in: $(pwd)"
