#!/usr/bin/env python3
"""Real local-model smoke tests in an isolated database. Never touches bakery records.

Default: exercise the HTTP model transport used by the app.
--cli: use an installed llama-completion executable instead of HTTP. Actual model
inference still runs, but this mode does NOT verify the running server/browser.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--cli', type=Path, help='Optional llama-completion binary for one-shot CPU inference')
parser.add_argument('--conflicts-only', action='store_true', help='Run only the conflicting-purchases regression')
args = parser.parse_args()

with tempfile.TemporaryDirectory(prefix='bentabuddy-real-ai-') as directory:
    os.environ['BENTABUDDY_DATA'] = directory
    from backend import app as backend
    import httpx

    def cli_transport(url, *, json, timeout):
        messages = json['messages']
        prompt = ''.join('<|im_start|>' + m['role'] + '\n' + m['content'] + '<|im_end|>\n' for m in messages) + '<|im_start|>assistant\n'
        prompt_path = Path(directory) / 'prompt.txt'
        schema_path = Path(directory) / 'schema.json'
        prompt_path.write_text(prompt)
        schema_path.write_text(backend.dump(json.get('response_format',{}).get('json_schema',{}).get('schema',json.get('format',backend.SCHEMA))))
        completed = subprocess.run([str(args.cli.resolve()), '-m', str(ROOT / '.runtime/models/qwen3-4b-instruct-2507.gguf'),
                                    '-f', str(prompt_path), '-jf', str(schema_path), '-n', '2200', '-c', '4096', '-t', '4',
                                    '--device', 'none', '-ngl', '0', '--no-op-offload', '--no-kv-offload', '--fit', 'off',
                                    '--temp', '0', '--no-display-prompt', '--no-conversation'],
                                   capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL)
        if completed.returncode:
            raise RuntimeError('One-shot inference failed: ' + completed.stderr[-700:])
        content = completed.stdout.strip()
        if content.endswith('[end of text]'):
            content = content[:-len('[end of text]')].strip()
        return httpx.Response(200, request=httpx.Request('POST', url), json={'choices': [{'finish_reason': 'stop', 'message': {'content': content}}]})

    def extract(text, linked=None):
        texts = text if isinstance(text, list) else [text]
        conversation = backend.import_message(backend.ImportBody(customer_name='Synthetic smoke-test buyer', text=texts[0], order_id=linked))
        for followup in texts[1:]:
            conversation = backend.import_message(backend.ImportBody(customer_name='Synthetic smoke-test buyer', text=followup, conversation_id=conversation['id']))
        with backend.connect() as db:
            for message in conversation['messages']:
                message['created_at'] = '2026-10-09T17:26:00+08:00'
            backend.write_payload(db, 'conversations', conversation)
            order = backend.read_payload(db, 'orders', linked) if linked else None
            job = dict(id=backend.uid('job'), conversation_id=conversation['id'], conversation_version=conversation['version'], order_version=order['version'] if order else None,
                       status='queued', created_at=backend.now(), model=backend.MODEL, proposal=None, error=None)
            backend.write_payload(db, 'jobs', job)
        started = time.monotonic()
        backend.run_job(job['id'])
        with backend.connect() as db:
            job = backend.read_payload(db, 'jobs', job['id'])
        if job['status'] != 'ready':
            raise AssertionError(job.get('error') or job['status'])
        return job, round(time.monotonic() - started, 2)

    def checks():
        print('Transport:', 'one-shot CPU CLI (HTTP/browser not tested)' if args.cli else 'localhost HTTP', flush=True)
        if args.conflicts_only:
            existing = backend.save_order(backend.OrderBody(customer_name='Synthetic smoke-test buyer', items=[dict(product_id='p_cookie',quantity=3,unit='piece')],due_date='2026-10-10',due_time='10:00',method='pickup'))
            check_conflicting_purchases(existing)
            return
        first, elapsed = extract('Ate, pa-order 2 dozen cheese pandesal bukas, pickup 8am. Gawin na lang 3 dozen, 9am na lang po.')
        p = first['proposal']
        assert p['action'] == 'new_order', p
        assert (p['due_date'], p['due_time'], p['method']) == ('2026-10-10', '09:00', 'pickup'), p
        order = backend.save_order(backend.OrderBody(customer_name='Synthetic smoke-test buyer', items=p['items'], due_date=p['due_date'], due_time=p['due_time'], method=p['method'], address=p['address'], notes=p['notes'], job_id=first['id']))
        assert len(order['items']) == 1 and order['items'][0]['product_id'] == 'p_pandesal' and order['items'][0]['base_quantity'] == 36, order
        print(f'PASS corrected new order: 36 pieces, October 10, 09:00 pickup ({elapsed}s)', flush=True)
        revised, elapsed = extract('Gawin na lang 4 dozen cheese pandesal. Same pickup date and time po.', linked=order['id'])
        p = revised['proposal']
        assert p['action'] == 'change', p
        assert (p['due_date'], p['due_time']) == ('2026-10-10', '09:00'), p
        saved = backend.save_order(backend.OrderBody(customer_name=order['customer_name'], items=p['items'], due_date=p['due_date'], due_time=p['due_time'], method=p['method'], address=p['address'], notes=p['notes'], job_id=revised['id'], version=order['version']), order['id'])
        assert saved['id'] == order['id'] and saved['items'][0]['base_quantity'] == 48, saved
        print(f'PASS revision: same order, 48 pieces, original pickup preserved ({elapsed}s)', flush=True)
        inquiry, elapsed = extract('Magkano po cheese pandesal? Available po ba bukas?')
        assert inquiry['proposal']['action'] == 'inquiry', inquiry['proposal']
        print(f'PASS inquiry is not a purchase ({elapsed}s)', flush=True)
        for action in ['preparing', 'ready', 'fulfilled']:
            saved = backend.transition(saved['id'], backend.TransitionBody(action=action, version=saved['version']))
        conversation = backend.import_message(backend.ImportBody(customer_name=order['customer_name'], conversation_id=revised['conversation_id'], text='Pa-order naman 3 chocolate chip cookies bukas, pickup 10am.'))
        with backend.connect() as db:
            conversation['messages'][-1]['created_at'] = '2026-10-09T20:30:00+08:00'
            backend.write_payload(db, 'conversations', conversation)
        with patch.object(backend.WORKER, 'submit'):
            returning = backend.analyze(conversation['id'])
        backend.run_job(returning['id'])
        with backend.connect() as db:
            returning = backend.read_payload(db, 'jobs', returning['id'])
        assert returning['status'] == 'ready', returning
        p = returning['proposal']
        assert p['action'] == 'new_order', p
        assert p['items'] == [dict(product_id='p_cookie', quantity=3, unit='piece')], p
        assert (p['due_date'], p['due_time'], p['method']) == ('2026-10-10', '10:00', 'pickup'), p
        new_order = backend.save_order(backend.OrderBody(customer_name=order['customer_name'], items=p['items'], due_date=p['due_date'], due_time=p['due_time'], method=p['method'], job_id=returning['id']))
        assert new_order['id'] != saved['id'] and new_order['customer_id'] == saved['customer_id'], new_order
        print('PASS returning customer: only 3 cookies, separate order; old pandesal excluded', flush=True)
        check_conflicting_purchases(new_order)
        print('All real inference checks passed. Synthetic test database discarded.', flush=True)

    def check_conflicting_purchases(new_order):
        conflicting, elapsed = extract([
            'Hi can I order 1 cake and 3 cookies',
            'I want it delivered to the same address by 5pm',
            'Separate order po: 2 cookies and 1 cake. Pickup later at 10am.',
            'Sorry 10 cookies na pala',
        ], linked=new_order['id'])
        assert conflicting['proposal']['action'] == 'needs_clarification', conflicting['proposal']
        assert conflicting['proposal']['items'] == [], conflicting['proposal']
        assert conflicting['proposal']['questions'], conflicting['proposal']
        print(f'PASS conflicting separate purchases: clarification instead of merging into open order ({elapsed}s)', flush=True)

    if args.cli:
        with patch.object(backend.httpx, 'post', side_effect=cli_transport):
            checks()
    else:
        checks()
