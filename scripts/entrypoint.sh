#!/usr/bin/env bash
set -euo pipefail

export PYTHONUNBUFFERED=1
export PYTHONPATH="/app/src-backend:${PYTHONPATH:-}"

# Ensure base folders exist for first run
mkdir -p "${BASE_DIR:-/app}"/html-drop "${BASE_DIR:-/app}"/pdf-export "${BASE_DIR:-/app}"/processing "${BASE_DIR:-/app}"/done-html

mode="${APP_MODE:-cli}"
case "$mode" in
  api)
    exec python3 -m uvicorn api_service:app --host 0.0.0.0 --port "${PORT:-8000}" --workers "${WORKERS:-1}"
    ;;
  batch)
    exec python3 /app/scripts/batch_convert.py
    ;;
  cli)
    exec python3 /app/scripts/console_app.py
    ;;
  *)
    echo "Unknown APP_MODE: $mode (supported: api|batch|cli)" >&2
    exit 1
    ;;
esac


