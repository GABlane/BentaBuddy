#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")/.."
echo 'Phone access: connect the phone and Mac to the same trusted local network.'
echo 'There is no sign-in: anyone on this network can open the app while it runs. Use a trusted network or your own hotspot.'
exec env BENTABUDDY_HOST=0.0.0.0 ./scripts/start.sh
