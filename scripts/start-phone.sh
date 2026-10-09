#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo 'Phone access: connect the phone and Mac to the same trusted local network.'
echo 'Sign in with your existing bakery owner account on the phone.'
exec env BENTABUDDY_HOST=0.0.0.0 ./scripts/start.sh
