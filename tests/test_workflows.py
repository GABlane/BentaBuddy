"""Business workflow tests. Model transport is mocked; these are not AI accuracy tests."""
import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Never open the user's bakery database from tests.
_TEST_DATA = tempfile.TemporaryDirectory()
os.environ['BENTABUDDY_DATA'] = _TEST_DATA.name
from backend import app as backend
from fastapi.testclient import TestClient


class Workflows(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_db = backend.DB
        backend.DB = Path(self.directory.name) / 'test.sqlite3'
        backend.init_db()
        self.client = TestClient(backend.app)
        response = self.client.post('/api/auth/setup', json=dict(email='owner@example.test', password='test-password-123', bakery_name='Test bakery'))
        self.assertEqual(response.status_code, 200, response.text)

    def tearDown(self):
        self.client.close()
        backend.DB = self.original_db
        self.directory.cleanup()

    def body(self, **changes):
        body = dict(customer_name='Test buyer', items=[dict(product_id='p_pandesal', quantity=3, unit='dozen')],
                    due_date=backend.today(), due_time='09:00', method='pickup', address='', notes='', is_demo=False)
        body.update(changes)
        return body

    def create(self, **changes):
        response = self.client.post('/api/orders', json=self.body(**changes))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def advance(self, order, action):
        response = self.client.post('/api/orders/' + order['id'] + '/transition', json=dict(action=action, version=order['version']))
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def proposal(self):
        return dict(action='new_order', items=[dict(product_id='p_pandesal', quantity=3, unit='dozen')],
                    due_date=backend.today(), due_time='09:00', method='pickup', address='', notes='', questions=[],
                    evidence=[dict(message_id='m_demo_2', quote='3 dozen')])

    def test_login_protects_bakery_data_and_logout_revokes_session(self):
        with TestClient(backend.app) as visitor:
            self.assertEqual(visitor.get('/api/state').status_code, 401)
            self.assertEqual(visitor.post('/api/orders', json=self.body()).status_code, 401)
            visitor.cookies.set('bentabuddy_session', 'forged-cookie')
            self.assertEqual(visitor.get('/api/state').status_code, 401)
            visitor.cookies.clear()
            bad = visitor.post('/api/auth/login', json=dict(email='owner@example.test', password='incorrect'))
            self.assertEqual(bad.status_code, 401)
            login = visitor.post('/api/auth/login', json=dict(email='OWNER@example.test', password='test-password-123'))
            self.assertEqual(login.status_code, 200)
            self.assertIn('HttpOnly', login.headers['set-cookie'])
            self.assertIn('SameSite=strict', login.headers['set-cookie'])
            self.assertEqual(visitor.get('/api/state').status_code, 200)
            token = visitor.cookies.get('bentabuddy_session')
            self.assertEqual(visitor.post('/api/auth/logout', json={}).status_code, 200)
            visitor.cookies.set('bentabuddy_session', token)
            self.assertEqual(visitor.get('/api/state').status_code, 401)

    def test_owner_password_is_hashed_and_setup_cannot_overwrite_account(self):
        self.assertFalse(self.client.get('/api/auth/status').json()['needs_setup'])
        with backend.connect() as db:
            owner = db.execute('SELECT * FROM auth_owner').fetchone()
            self.assertNotEqual(owner['password_hash'], 'test-password-123')
            self.assertEqual(len(owner['salt']), 32)
            self.assertEqual(len(owner['password_hash']), 64)
        response = self.client.post('/api/auth/setup', json=dict(email='another@example.test', password='other-password-123', bakery_name='Another bakery'))
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.client.get('/api/auth/status').json()['user']['bakery_name'], 'Test bakery')

    def test_cross_site_mutations_and_expired_sessions_are_rejected(self):
        self.assertEqual(self.client.post('/api/orders', json=self.body(), headers={'origin':'https://other.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/auth/logout', content='').status_code, 403)
        with backend.connect() as db:
            db.execute('UPDATE auth_sessions SET expires_at=0')
        self.assertEqual(self.client.get('/api/state').status_code, 401)
        self.assertIsNone(self.client.get('/api/auth/status').json()['user'])

    def test_dozen_converts_to_pieces_and_catalog_price(self):
        order = self.create()
        self.assertEqual(order['items'][0]['base_quantity'], 36)
        self.assertEqual(order['total_cents'], 43200)
        self.assertFalse(order['is_demo'])

    def test_same_name_does_not_merge_customers(self):
        self.assertNotEqual(self.create()['customer_id'], self.create()['customer_id'])

    def test_invalid_quantity_unit_and_shape_rejected(self):
        for item in [dict(product_id='p_pandesal', quantity=True, unit='piece'),
                     dict(product_id='p_pandesal', quantity=1, unit='kilogram'), 'invalid']:
            response = self.client.post('/api/orders', json=self.body(items=[item]))
            self.assertEqual(response.status_code, 400)

    def test_delivery_requires_address(self):
        self.assertEqual(self.client.post('/api/orders', json=self.body(method='delivery')).status_code, 400)

    def test_revision_keeps_order_id_and_requeues_changed_food(self):
        order = self.advance(self.advance(self.create(), 'preparing'), 'ready')
        revised = self.client.put('/api/orders/' + order['id'], json=self.body(version=order['version'], items=[dict(product_id='p_pandesal', quantity=4, unit='dozen')]))
        self.assertEqual(revised.status_code, 200)
        self.assertEqual(revised.json()['id'], order['id'])
        self.assertEqual(revised.json()['fulfillment'], 'queued')
        self.assertEqual(revised.json()['items'][0]['base_quantity'], 48)
        self.assertEqual(self.client.put('/api/orders/' + order['id'], json=self.body(version=1)).status_code, 409)

    def test_delivery_and_pickup_have_different_handoff(self):
        for method in ['pickup', 'delivery']:
            order = self.create(method=method, address='Test address' if method == 'delivery' else '')
            self.assertEqual(self.client.post('/api/orders/' + order['id'] + '/transition', json=dict(action='fulfilled', version=order['version'])).status_code, 400)
            order = self.advance(self.advance(order, 'preparing'), 'ready')
            if method == 'delivery':
                order = self.advance(order, 'out_for_delivery')
                self.assertEqual(self.client.put('/api/orders/' + order['id'], json=self.body(version=order['version'], method='delivery', address='Test address', items=[dict(product_id='p_cookie', quantity=1, unit='piece')])).status_code, 400)
            order = self.advance(order, 'fulfilled')
            self.assertIsNotNone(order['fulfilled_at'])
            self.assertEqual(order['paid_cents'], 0)
            self.assertEqual(self.client.put('/api/orders/' + order['id'], json=self.body(version=order['version'])).status_code, 400)

    def test_payment_is_idempotent_and_independent_of_fulfillment(self):
        order = self.create()
        body = dict(amount_cents=12000, method='gcash', version=order['version'], idempotency_key='payment_test_1')
        path = '/api/orders/' + order['id'] + '/payments'
        first = self.client.post(path, json=body).json()
        duplicate = self.client.post(path, json=body).json()
        self.assertEqual(first, duplicate)
        self.assertEqual(first['paid_cents'], 12000)
        self.assertEqual(first['fulfillment'], 'queued')
        self.assertEqual(self.client.post(path, json=dict(body, amount_cents=999999, version=first['version'], idempotency_key='payment_test_2')).status_code, 400)
        self.assertEqual(self.client.put('/api/orders/' + order['id'], json=self.body(version=first['version'], items=[dict(product_id='p_pandesal', quantity=1, unit='piece')])).status_code, 400)

    def test_cancellation_closes_order_and_retains_payment_history(self):
        order = self.create()
        order = self.client.post('/api/orders/' + order['id'] + '/payments', json=dict(amount_cents=12000, method='cash', version=1, idempotency_key='payment_cancel')).json()
        order = self.advance(order, 'cancel')
        self.assertEqual(order['state'], 'canceled')
        self.assertEqual(order['paid_cents'], 12000)
        self.assertEqual(self.client.put('/api/orders/' + order['id'], json=self.body(version=order['version'])).status_code, 400)
        history = self.client.get('/api/orders/' + order['id'] + '/history').json()
        self.assertEqual([e['kind'] for e in history], ['confirmed', 'payment', 'cancel'])

    def test_empty_or_truncated_model_responses_are_readable_errors(self):
        for response in [
            dict(choices=[dict(finish_reason='length', message=dict(content='', reasoning_content='thinking'))]),
            dict(choices=[dict(finish_reason='stop', message=dict(content=''))]),
            dict(choices=[dict(finish_reason='stop', message=dict(content='{"action":'))]),
        ]:
            with self.assertRaises(ValueError) as failure:
                backend.parse_model_response(response, 'llamacpp')
            self.assertNotIn('Expecting value', str(failure.exception))
        with self.assertRaisesRegex(ValueError, 'output limit'):
            backend.parse_model_response(dict(message=dict(content='{}'), done_reason='length'), 'ollama')

    def test_model_parser_accepts_final_json_but_never_reasoning(self):
        expected = self.proposal()
        payload = json.dumps(expected)
        for content in [payload, '```json\n' + payload + '\n```']:
            response = dict(choices=[dict(finish_reason='stop', message=dict(content=content, reasoning_content='untrusted thinking'))])
            self.assertEqual(backend.parse_model_response(response, 'llamacpp'), expected)
        self.assertEqual(backend.parse_model_response(dict(message=dict(content=payload), done_reason='stop'), 'ollama'), expected)

    def test_model_proposal_requires_real_source_quote(self):
        with backend.connect() as db:
            conv = backend.read_payload(db, 'conversations', 'conv_demo')
            proposal = self.proposal()
            backend.validate_proposal(db, proposal, conv)
            proposal['evidence'][0]['quote'] = 'invented quote'
            with self.assertRaises(ValueError):
                backend.validate_proposal(db, proposal, conv)

    def test_ai_runs_locally_and_requires_approval(self):
        response = unittest.mock.Mock()
        response.json.return_value = dict(choices=[dict(message=dict(content=json.dumps(self.proposal())))])
        with patch.object(backend.WORKER, 'submit'):
            job = self.client.post('/api/conversations/conv_demo/analyze', json={}).json()
        with patch.object(backend.httpx, 'post', return_value=response) as transport:
            backend.run_job(job['id'])
        self.assertEqual(transport.call_args.kwargs['json']['reasoning_budget'], 0)
        self.assertFalse(transport.call_args.kwargs['json']['chat_template_kwargs']['enable_thinking'])
        self.assertEqual(transport.call_args.args[0], 'http://127.0.0.1:11434/v1/chat/completions')
        state = self.client.get('/api/state').json()
        self.assertEqual(len(state['orders']), 55)
        self.assertEqual(state['jobs'][0]['status'], 'ready')
        approved = self.client.post('/api/orders', json=self.body(job_id=job['id']))
        self.assertEqual(approved.status_code, 200, approved.text)
        self.assertTrue(approved.json()['is_demo'])
        self.assertEqual(self.client.post('/api/orders', json=self.body(job_id=job['id'])).status_code, 409)

    def test_new_message_makes_proposal_stale(self):
        with patch.object(backend.WORKER, 'submit'):
            job = self.client.post('/api/conversations/conv_demo/analyze', json={}).json()
        with backend.connect() as db:
            job.update(status='ready', proposal=self.proposal())
            backend.write_payload(db, 'jobs', job)
        self.client.post('/api/conversations', json=dict(customer_name='Mika', text='Cancel please', conversation_id='conv_demo'))
        self.assertEqual(self.client.post('/api/orders', json=self.body(job_id=job['id'])).status_code, 409)

    def test_returning_buyer_can_start_new_order_in_same_thread(self):
        first = self.advance(self.advance(self.advance(self.create(), 'preparing'), 'ready'), 'fulfilled')
        with backend.connect() as db:
            conv = backend.read_payload(db, 'conversations', 'conv_demo')
            conv['linked_order_id'] = first['id']
            conv['customer_id'] = first['customer_id']
            conv['is_demo'] = False
            backend.write_payload(db, 'conversations', conv)
        with patch.object(backend.WORKER, 'submit'):
            job = self.client.post('/api/conversations/conv_demo/analyze', json={}).json()
        with backend.connect() as db:
            job.update(status='ready', proposal=self.proposal())
            backend.write_payload(db, 'jobs', job)
        second = self.client.post('/api/orders', json=self.body(job_id=job['id']))
        self.assertEqual(second.status_code, 200, second.text)
        self.assertNotEqual(second.json()['id'], first['id'])
        self.assertEqual(second.json()['customer_id'], first['customer_id'])
        self.assertEqual(second.json()['fulfillment'], 'queued')

    def test_restart_recovers_interrupted_jobs_and_preserves_orders(self):
        with patch.object(backend.WORKER, 'submit'):
            self.client.post('/api/conversations/conv_demo/analyze', json={})
        order = self.create()
        backend.init_db()
        state = self.client.get('/api/state').json()
        self.assertEqual(state['jobs'][0]['status'], 'failed')
        self.assertIn(order['id'], [o['id'] for o in state['orders']])

    def test_signed_facebook_webhooks_are_deduplicated(self):
        payload = dict(object='page', entry=[dict(id='test_page', messaging=[dict(sender=dict(id='customer1'), message=dict(mid='message1', text='3 dozen pandesal bukas 9am pickup'))])])
        raw = json.dumps(payload).encode()
        signature = 'sha256=' + hmac.new(b'test-secret', raw, hashlib.sha256).hexdigest()
        with patch.dict(os.environ, META_APP_SECRET='test-secret', META_VERIFY_TOKEN='verify', META_PAGE_ID='test_page'), patch.object(backend.WORKER, 'submit'):
            self.assertEqual(self.client.post('/api/facebook/webhook', content=raw).status_code, 403)
            for _ in range(2):
                response = self.client.post('/api/facebook/webhook', content=raw, headers={'x-hub-signature-256': signature})
                self.assertEqual(response.status_code, 200)
            self.assertEqual(self.client.get('/api/facebook/webhook?hub.mode=subscribe&hub.verify_token=verify&hub.challenge=123').text, '123')
        state = self.client.get('/api/state').json()
        facebook = [c for c in state['conversations'] if c['source'] == 'facebook']
        self.assertEqual(len(facebook), 1)
        self.assertEqual(len(facebook[0]['messages']), 1)
        self.assertFalse(facebook[0]['is_demo'])
        self.assertEqual(len(state['jobs']), 1)


if __name__ == '__main__':
    unittest.main()
