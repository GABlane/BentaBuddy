#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
command -v node >/dev/null || { echo 'Install Node.js 22 or newer.' >&2; exit 1; }
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
npm ci
npm run build
if [[ "${BENTABUDDY_RUNTIME:-llamacpp}" == "ollama" ]]; then
  echo 'Run ollama pull qwen3:4b-instruct-2507-q4_K_M, then ./scripts/start.sh with BENTABUDDY_RUNTIME=ollama.'
  exit 0
fi
if [[ "$(uname -s)" != Darwin || "$(uname -m)" != arm64 ]]; then
  echo 'Bundled runtime setup targets Apple silicon. Install Ollama, pull qwen3:4b-instruct-2507-q4_K_M, and set BENTABUDDY_RUNTIME=ollama.' >&2
  exit 1
fi
mkdir -p .runtime/ollama .runtime/models
if [[ ! -x .runtime/ollama/llama-server ]]; then
  curl --fail --location --retry 3 https://github.com/ollama/ollama/releases/download/v0.40.2/ollama-darwin.tgz -o .runtime/runtime.tgz
  tar -xzf .runtime/runtime.tgz -C .runtime/ollama
  rm .runtime/runtime.tgz
fi
model_path=.runtime/models/qwen3-4b-instruct-2507.gguf
if [[ ! -f "$model_path" ]]; then
  curl --fail --location --retry 3 https://registry.ollama.ai/v2/library/qwen3/blobs/sha256:85e4a5b7b8ef0e48af0e8658f5aaab9c2324c76c1641493f4d1e25fce54b18b9 -o "$model_path.part"
  mv "$model_path.part" "$model_path"
fi
echo '85e4a5b7b8ef0e48af0e8658f5aaab9c2324c76c1641493f4d1e25fce54b18b9  .runtime/models/qwen3-4b-instruct-2507.gguf' | shasum -a 256 -c -
echo 'Ready. Run ./scripts/start.sh'
