#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ ! -x .venv/bin/python ]]; then echo 'Run ./scripts/setup.sh first.' >&2; exit 1; fi
if [[ -f .env ]]; then set -a; source .env; set +a; fi
if [[ -z "${META_APP_SECRET:-}" || -z "${META_VERIFY_TOKEN:-}" || -z "${META_PAGE_ID:-}" ]]; then
  echo 'First run: .venv/bin/python -B scripts/configure-facebook.py' >&2
  exit 1
fi
# Validate the verification handshake before opening a public tunnel.
.venv/bin/python -B - <<'PY'
import os, httpx
try:
    response=httpx.get('http://127.0.0.1:8000/api/facebook/webhook', params={'hub.mode':'subscribe','hub.verify_token':os.environ['META_VERIFY_TOKEN'],'hub.challenge':'bentabuddy-ready'}, timeout=5)
    assert response.status_code==200 and response.text=='bentabuddy-ready'
except Exception:
    raise SystemExit('BentaBuddy is not running with these settings. Restart ./scripts/start.sh in another Terminal first.')
PY
cloudflared_bin=$(command -v cloudflared || true)
if [[ -z "$cloudflared_bin" ]]; then
  mkdir -p .runtime/cloudflared
  cloudflared_bin="$PWD/.runtime/cloudflared/cloudflared"
  if [[ ! -x "$cloudflared_bin" ]]; then
    if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
      echo 'Install cloudflared for your platform, then run this script again.' >&2; exit 1
    fi
    echo 'Downloading the official Cloudflare tunnel client for this Mac…'
    curl --fail --location --retry 3 https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-arm64.tgz -o .runtime/cloudflared/client.tgz
    tar -xzf .runtime/cloudflared/client.tgz -C .runtime/cloudflared
    chmod +x "$cloudflared_bin"
  fi
fi
mkdir -p data
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m uvicorn backend.facebook_relay:app --host 127.0.0.1 --port 8001 >data/facebook-relay.log 2>&1 &
relay_pid=$!
trap 'kill "$relay_pid" 2>/dev/null || true' EXIT
trap 'exit 130' INT TERM
sleep 1
kill -0 "$relay_pid" 2>/dev/null || { echo 'Relay failed to start. See data/facebook-relay.log.' >&2; exit 1; }
echo
echo 'Copy the https://….trycloudflare.com address printed below.'
echo 'Meta Callback URL = that address + /api/facebook/webhook'
echo 'Keep this Terminal and BentaBuddy running. Ctrl+C stops the tunnel.'
echo 'Only the webhook is forwarded; the dashboard stays private.'
echo
"$cloudflared_bin" tunnel --url http://127.0.0.1:8001 --protocol http2 --no-autoupdate
