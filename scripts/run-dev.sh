#!/usr/bin/env bash
# Start the API locally with auto-reload. Uses .env if present.
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -d ".venv" ]; then
  python -m venv .venv
  ./.venv/Scripts/python -m pip install --upgrade pip
  ./.venv/Scripts/python -m pip install -r requirements-dev.txt
fi

./.venv/Scripts/python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
