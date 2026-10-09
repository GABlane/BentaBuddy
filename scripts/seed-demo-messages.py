#!/usr/bin/env python3
"""Add sample inbox conversations for every business type once, or remove them with --remove. Backs up first."""
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.sample_conversations import remove_sample_conversations, seed_sample_conversations

root = Path(__file__).resolve().parent.parent
data = Path(os.environ.get('BENTABUDDY_DATA', str(root/'data')))
path = data/'bentabuddy.sqlite3'
if not path.exists():
    raise SystemExit('Start BentaBuddy once to initialize its database.')
remove = '--remove' in sys.argv[1:]
backup = data/'backups'/(('before-remove-demo-messages-' if remove else 'before-seed-demo-messages-')+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
backup.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(str(path), timeout=15) as db:
    db.row_factory = sqlite3.Row
    with sqlite3.connect(str(backup)) as target:
        db.backup(target)
    db.execute('BEGIN IMMEDIATE')
    if remove:
        print('Removed', remove_sample_conversations(db), 'sample conversations. Orders you confirmed from them were kept.')
    else:
        print('Added', seed_sample_conversations(db), 'sample conversations (4 bakery, 4 gadgets, 3 staycation, 3 general when first run).')
print('Backup:', backup)
