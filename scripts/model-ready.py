"""Exit 0 for the configured model, 1 if offline, 2 for a mismatched runtime/model."""
import os
import sys
import httpx

runtime = os.environ.get('BENTABUDDY_RUNTIME', 'llamacpp')
model = os.environ.get('BENTABUDDY_MODEL', 'qwen3:4b-instruct-2507-q4_K_M')
for endpoint in ['/v1/models', '/api/tags'] if runtime == 'llamacpp' else ['/api/tags', '/v1/models']:
    try:
        response = httpx.get('http://127.0.0.1:11434' + endpoint, timeout=2)
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError):
        continue
    names = [m.get('id') for m in data.get('data', [])] if runtime == 'llamacpp' else [m.get('name') for m in data.get('models', [])]
    sys.exit(0 if model in names else 2)
sys.exit(1)
