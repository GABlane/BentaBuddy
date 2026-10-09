#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python || ! -f dist/index.html ]]; then
  echo 'App dependencies/build missing. Run ./scripts/setup.sh first.' >&2
  exit 1
fi
# Optional local secrets. Never expose these through Vite or commit .env.
if [[ -f .env ]]; then set -a; source .env; set +a; fi
mkdir -p data
ai_pid=''
cleanup() { if [[ -n "$ai_pid" ]]; then kill "$ai_pid" 2>/dev/null || true; fi; }
trap cleanup EXIT INT TERM
probe_status=0
.venv/bin/python -B scripts/model-ready.py || probe_status=$?
if [[ "$probe_status" == 2 ]]; then
  echo 'A different local model is already running on port 11434.' >&2
  echo 'Stop that AI server, then run ./scripts/start.sh again to load the bakery Instruct model.' >&2
  exit 1
fi
if [[ "$probe_status" != 0 ]]; then
  ./scripts/start-ai.sh >data/local-ai.log 2>&1 &
  ai_pid=$!
  echo 'Loading the local model. Log: data/local-ai.log'
fi
echo 'BentaBuddy: http://127.0.0.1:8000'
echo 'Keep this Terminal open. Press Ctrl+C to stop.'
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m uvicorn backend.app:app --host "${BENTABUDDY_HOST:-127.0.0.1}" --port 8000
