#!/usr/bin/env python3
"""Clear demo activity with a local SQLite backup. Catalog and credentials stay saved."""
import json
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.demo_data import clear_demo

root = Path(__file__).resolve().parent.parent
data = Path(os.environ.get('BENTABUDDY_DATA', str(root / 'data')))
path = data / 'bentabuddy.sqlite3'
if not path.exists():
    raise SystemExit('No existing BentaBuddy database found.')
backup = data / 'backups' / ('before-clear-demo-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.sqlite3')
backup.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(str(path), timeout=15) as db:
    db.row_factory = sqlite3.Row
    with sqlite3.connect(str(backup)) as target:
        db.backup(target)
    db.execute('BEGIN IMMEDIATE')
    preserved = {table: {r['id']: r['payload'] for r in db.execute('SELECT id,payload FROM '+table)
                        if not json.loads(r['payload']).get('is_demo') and json.loads(r['payload']).get('source') != 'demo'}
                 for table in ('orders', 'customers', 'conversations')}
    counts = clear_demo(db)
    for table, records in preserved.items():
        for key, payload in records.items():
            row = db.execute('SELECT payload FROM '+table+' WHERE id=?', (key,)).fetchone()
            if not row or row['payload'] != payload:
                raise RuntimeError('Real record preservation check failed; transaction rolled back.')
    print('Removed demo records:', json.dumps(counts))
    print('Backup:', backup)
    print('Real orders, messages, customers, catalog, and credentials preserved.')
