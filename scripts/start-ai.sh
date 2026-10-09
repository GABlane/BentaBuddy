#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "${BENTABUDDY_RUNTIME:-llamacpp}" == "ollama" ]]; then
  exec ollama serve
fi
if [[ ! -x .runtime/ollama/llama-server || ! -f .runtime/models/qwen3-4b-instruct-2507.gguf ]]; then
  echo 'Local model missing. Run ./scripts/setup.sh first.' >&2
  exit 1
fi
exec .runtime/ollama/llama-server \
  -m .runtime/models/qwen3-4b-instruct-2507.gguf --alias "${BENTABUDDY_MODEL:-qwen3:4b-instruct-2507-q4_K_M}" \
  --host 127.0.0.1 --port 11434 -c 8192 -np 1 -ngl 99 \
  --reasoning off --reasoning-budget 0 --chat-template-kwargs '{"enable_thinking":false}' --no-webui
