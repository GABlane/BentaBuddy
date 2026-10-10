#!/usr/bin/env python3
"""Real local model checks using fictional orders; never calls Meta or the live DB."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from backend.customer_replies import reply_request

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cli', type=Path, required=True)
args = parser.parse_args()
base = dict(id='food', number='BB-1001', business_kind='bakery', state='confirmed', fulfillment='preparing', method='pickup', due_date='2026-11-20', due_time='10:00', items=[dict(name='Pandesal', quantity=20, unit='piece')])
gadget = dict(base, id='gadget', number='BB-1002', business_kind='gadgets', fulfillment='out_for_delivery', method='delivery', items=[dict(name='USB-C cable', quantity=1, unit='piece')])
stay = dict(base, id='stay', number='BB-1003', business_kind='staycation', reservation=dict(status='pending', check_in='2026-11-20', check_out='2026-11-22', guests=2), items=[dict(name='Studio stay', quantity=2, unit='night')])
cases = [
    ('kitchen', 'Luto na po yung BB-1001?', [base], 'status:food'),
    ('dispatch', 'Na dispatch na po yung BB-1002?', [gadget], 'status:gadget'),
    ('pending booking', 'Confirmed na ba booking BB-1003?', [stay], 'status:stay'),
    ('ambiguous orders', 'Ano status ng order ko?', [base, gadget], 'clarify'),
    ('new request', 'Pa order po 30 cookies bukas 10am pickup.', [base], 'receipt'),
    ('unknown reference', 'Status po ng BB-9999?', [base], 'clarify'),
]
with tempfile.TemporaryDirectory() as directory:
    for label, message, orders, expected in cases:
        _, body, choices = reply_request(message, orders, 'llamacpp', 'local-model')
        prompt = ''.join('<|im_start|>'+m['role']+'\n'+m['content']+'<|im_end|>\n' for m in body['messages'])+'<|im_start|>assistant\n'
        prompt_path = Path(directory)/'prompt.txt'
        prompt_path.write_text(prompt)
        schema_path = Path(directory)/'schema.json'
        schema_path.write_text(json.dumps(body['response_format']['json_schema']['schema']))
        result = subprocess.run([str(args.cli.resolve()), '-m', str(ROOT/'.runtime/models/qwen3-4b-instruct-2507.gguf'), '-f', str(prompt_path), '-jf', str(schema_path), '-n', '120', '-c', '4096', '-t', '4', '--device', 'none', '-ngl', '0', '--no-op-offload', '--no-kv-offload', '--fit', 'off', '--temp', '0', '--no-display-prompt', '--no-conversation'], capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
        if result.returncode:
            raise RuntimeError(result.stderr[-700:])
        content = result.stdout.strip().removesuffix('[end of text]').strip()
        selection = json.loads(content)['reply_id']
        assert selection == expected, f'{label}: expected {expected}, got {selection}'
        assert selection in choices
        print(f'{label}: PASS ({selection})', flush=True)
