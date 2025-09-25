#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/venvs/graph"

# Create venv if missing
if [ ! -d "$VENV_DIR" ]; then
  echo "[INFO] Creating virtualenv at $VENV_DIR"
  python3 -m venv "$VENV_DIR"
  source "$VENV_DIR/bin/activate"
  pip install --upgrade pip
  pip install fastapi uvicorn neo4j pyyaml
else
  source "$VENV_DIR/bin/activate"
fi

# Run the FastAPI server
exec uvicorn graph_api:app --reload --port 8000

