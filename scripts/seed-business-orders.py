#!/usr/bin/env python3
"""Add clearly labeled sample orders once, preserving existing activity."""
import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend.sample_orders import seed_sample_orders

root = Path(__file__).resolve().parent.parent
data = Path(os.environ.get('BENTABUDDY_DATA', str(root/'data')))
path = data/'bentabuddy.sqlite3'
if not path.exists():
    raise SystemExit('Start BentaBuddy once to initialize its database.')
backup = data/'backups'/('before-seed-business-orders-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.sqlite3')
backup.parent.mkdir(parents=True, exist_ok=True)
with sqlite3.connect(str(path), timeout=15) as db:
    db.row_factory = sqlite3.Row
    with sqlite3.connect(str(backup)) as target:
        db.backup(target)
    db.execute('BEGIN IMMEDIATE')
    count = seed_sample_orders(db)
print('Added', count, 'sample orders to the live workspace (3 gadgets, 3 staycation when first run).')
print('Existing records preserved. Backup:', backup)
