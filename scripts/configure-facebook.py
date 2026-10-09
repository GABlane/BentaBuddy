#!/usr/bin/env python3
"""Collect Meta credentials locally; never paste secrets into chat or commit them."""
import getpass
from pathlib import Path
import re
import secrets
import shlex

root = Path(__file__).resolve().parent.parent
print('In Meta, open App settings → Basic to find the App Secret.')
secret = getpass.getpass('App Secret (hidden): ').strip()
if not re.fullmatch(r'[A-Fa-f0-9]{32,64}', secret):
    raise SystemExit('Expected the hexadecimal App Secret from Meta App settings → Basic.')
page_id = input('Page ID for The Bakery Dev (digits): ').strip()
if not page_id.isdigit():
    raise SystemExit('Enter the numeric Page ID, not the Page name or URL.')
token = secrets.token_urlsafe(32)
path = root / '.env'
existing = path.read_text() if path.exists() else ''
keys = ['META_APP_SECRET', 'META_VERIFY_TOKEN', 'META_PAGE_ID']
lines = [line for line in existing.splitlines() if not any(re.match(r'^\s*(?:export\s+)?' + key + r'\s*=', line) for key in keys)]
for key, value in zip(keys, [secret, token, page_id]):
    lines.append(key + '=' + shlex.quote(value))
path.touch(mode=0o600, exist_ok=True)
path.chmod(0o600)
path.write_text('\n'.join(lines) + '\n')
print('\nSaved credentials in your ignored local .env file.')
print('Copy this into the Meta Verify token field:')
print(token)
print('\nRestart BentaBuddy with ./scripts/start.sh to load the settings.')
print('Then, in a second Terminal, run ./scripts/start-facebook.sh for the HTTPS callback URL.')
