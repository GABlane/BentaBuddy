#!/usr/bin/env python3
"""Save a Page access token locally without changing verified webhook credentials."""
import getpass
import re
import shlex
from pathlib import Path

path = Path(__file__).resolve().parent.parent / '.env'
token = getpass.getpass('New Page access token for The Bakery Dev (hidden): ').strip()
if not re.fullmatch(r'[A-Za-z0-9_-]{40,}', token):
    raise SystemExit('Expected a Page access token from Meta Messenger API Settings.')
existing = path.read_text() if path.exists() else ''
lines = [line for line in existing.splitlines() if not re.match(r'^\s*(?:export\s+)?META_PAGE_ACCESS_TOKEN\s*=', line)]
lines.append('META_PAGE_ACCESS_TOKEN=' + shlex.quote(token))
path.touch(mode=0o600, exist_ok=True)
path.chmod(0o600)
path.write_text('\n'.join(lines) + '\n')
print('Page access token saved privately. Existing webhook settings preserved.')
print('Restart BentaBuddy with ./scripts/start.sh; keep the tunnel Terminal open.')
print('Then send the Page another message, or use Refresh customer profiles in Settings.')
