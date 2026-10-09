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
        with backend.connect() as db:
            backend.seed(db, include_demo=True)
        self.client = TestClient(backend.app)

    def tearDown(self):
        self.client.close()
        backend.DB = self.original_db
        self.directory.cleanup()

    def test_business_theme_persists_without_changing_records(self):
        before = self.client.get('/api/state').json()
        for kind in ('gadgets', 'staycation', 'general', 'bakery'):
            response = self.client.put('/api/business', json={'kind':kind,'name':'  My negosyo  '})
            self.assertEqual(response.status_code, 200, response.text)
            state = self.client.get('/api/state').json()
            self.assertEqual(state['business'], {'kind':kind,'name':'My negosyo'})
            for field in ('orders','customers','conversations'):
                self.assertEqual(state[field], before[field])
            for product in before['products']:
                self.assertEqual(next(p for p in state['all_products'] if p['id']==product['id']), product)
        self.assertEqual(self.client.put('/api/business', json={'kind':'unknown','name':'Shop'}).status_code, 400)
        self.assertEqual(self.client.put('/api/business', json={'kind':'gadgets','name':'   '}).status_code, 400)

    def test_gadget_catalog_and_local_ai_use_business_context(self):
        self.client.put('/api/business', json={'kind':'gadgets','name':'Gadget Suki'})
        result = self.client.post('/api/products', json={'name':'USB-C cable','category':'Accessories','price_cents':15000,'unit':'piece','aliases':['charging cable'],'emoji':'🔌'})
        self.assertEqual(result.status_code, 200, result.text)
        product = result.json()
        self.assertEqual(product['units'], {'piece':1})
        conversation = {'messages':[{'id':'test_message','text':'Pa-order 2 charging cables','created_at':backend.now()}]}
        _, request = backend.extraction_request(conversation, [product], None)
        prompt = request['messages'][0]['content']
        context = json.loads(request['messages'][1]['content'])
        self.assertIn('gadgets business', prompt)
        self.assertNotIn('You extract bakery orders', prompt)
        self.assertEqual(context['business']['name'], 'Gadget Suki')
        self.assertEqual(context['catalog'][0]['id'], product['id'])
        self.client.put('/api/business', json={'kind':'staycation','name':'Our Stay'})
        _, request = backend.extraction_request(conversation, [product], None)
        self.assertIn('never claim availability or confirm a booking', request['messages'][0]['content'])

    def test_business_catalog_switching_preserves_customized_offerings(self):
        self.client.put('/api/business', json={'kind':'staycation','name':'Our Stay'})
        state = self.client.get('/api/state').json()
        stays = backend.catalog_for(state['products'], 'staycation')
        self.assertEqual(len(stays), 4)
        self.assertTrue(all(p['active'] and p['price_cents']>0 and p['sample_pricing'] for p in stays))
        studio = next(p for p in stays if p['offering_type']=='accommodation')
        updated = dict(studio, name='Cozy studio', price_cents=250000, active=True)
        self.assertEqual(self.client.put('/api/products/'+studio['id'], json=updated).status_code, 200)
        order = self.create(items=[{'product_id':studio['id'],'quantity':2,'unit':'night'}], reservation={'product_id':studio['id'],'check_in':backend.today(),'check_out':(backend.datetime.now(backend.TZ)+backend.timedelta(days=2)).date().isoformat(),'guests':2,'status':'pending'})
        self.assertEqual(order['total_cents'], 500000)
        self.client.put('/api/business', json={'kind':'gadgets','name':'My Gadget Shop'})
        rejected = self.client.post('/api/orders', json=self.body(items=[{'product_id':studio['id'],'quantity':1,'unit':'night'}]))
        self.assertEqual(rejected.status_code, 400)
        self.client.put('/api/business', json={'kind':'staycation','name':'Our Stay'})
        state = self.client.get('/api/state').json()
        saved = next(p for p in state['products'] if p['id']==studio['id'])
        self.assertEqual(saved['name'], 'Cozy studio')
        self.assertEqual(saved['price_cents'], 250000)
        self.assertTrue(saved['active'])
        self.assertEqual(len(backend.catalog_for(state['products'], 'staycation')), 4)
        self.assertEqual(next(o for o in state['orders'] if o['id']==order['id'])['total_cents'], 500000)

    def test_local_ai_catalog_excludes_other_businesses_and_inactive_starters(self):
        self.client.put('/api/business', json={'kind':'gadgets','name':'Shop'})
        product = self.client.post('/api/products', json={'name':'Cable','category':'Accessories','price_cents':10000,'unit':'piece','aliases':['cable'],'active':True}).json()
        state = self.client.get('/api/state').json()
        starter = next(p for p in state['products'] if p['id']!=product['id'])
        self.client.put('/api/products/'+starter['id'], json=dict(starter, active=False))
        products = self.client.get('/api/state').json()['all_products']
        conversation = {'messages':[{'id':'m','text':'One cable please','created_at':backend.now()}]}
        _, request = backend.extraction_request(conversation, products, None)
        context = json.loads(request['messages'][1]['content'])
        self.assertEqual({p['id'] for p in context['catalog']}, {p['id'] for p in products if p.get('business_kind')=='gadgets' and p['active']})
        self.assertNotIn(starter['id'], [p['id'] for p in context['catalog']])
        conversation['is_demo'] = True
        _, request = backend.extraction_request(conversation, products, None)
        context = json.loads(request['messages'][1]['content'])
        self.assertEqual(context['business']['kind'], 'bakery')
        self.assertIn('p_pandesal', [p['id'] for p in context['catalog']])
        self.assertNotIn(product['id'], [p['id'] for p in context['catalog']])

    def test_state_catalog_tracks_business_switches_and_preserves_history(self):
        initial = self.client.get('/api/state').json()
        for kind in ('staycation', 'gadgets', 'general', 'bakery', 'staycation'):
            self.client.put('/api/business', json={'kind':kind,'name':'Test business'})
            state = self.client.get('/api/state').json()
            self.assertTrue(state['products'])
            self.assertTrue(all(p.get('business_kind', 'bakery')==kind for p in state['products']))
            self.assertEqual(state['orders'], initial['orders'])
            self.assertTrue(any(p['id']=='p_pandesal' for p in state['all_products']))
        self.assertEqual(self.client.get('/').headers.get('cache-control'), 'no-store, max-age=0')

    def test_theme_switch_preserves_disabled_starter_and_upgrades_only_untouched_drafts(self):
        self.client.put('/api/business', json={'kind':'gadgets','name':'Shop'})
        products = self.client.get('/api/state').json()['products']
        disabled, draft = products[:2]
        self.client.put('/api/products/'+disabled['id'], json=dict(disabled, active=False, price_cents=12345))
        legacy = dict(draft, price_cents=0, active=False,
                      description='Suggested offering. Edit the details and price before enabling requests.')
        legacy.pop('sample_pricing')
        with backend.connect() as db:
            backend.write_payload(db, 'products', legacy)
        for kind in ('staycation','gadgets'):
            self.client.put('/api/business', json={'kind':kind,'name':'Shop'})
        products = self.client.get('/api/state').json()['products']
        saved = next(p for p in products if p['id']==disabled['id'])
        upgraded = next(p for p in products if p['id']==draft['id'])
        self.assertFalse(saved['active'])
        self.assertEqual(saved['price_cents'], 12345)
        self.assertFalse(saved['sample_pricing'])
        self.assertTrue(upgraded['active'])
        self.assertTrue(upgraded['sample_pricing'])
        self.assertGreater(upgraded['price_cents'], 0)

    def test_fresh_install_does_not_seed_demo_activity(self):
        original = backend.DB
        try:
            backend.DB = Path(self.directory.name) / 'fresh.sqlite3'
            backend.init_db()
            with backend.connect() as db:
                for table in ('orders','customers','conversations','jobs'):
                    self.assertEqual(backend.payloads(db, table), [])
                self.assertTrue(backend.payloads(db, 'products'))
        finally:
            backend.DB = original

    def test_sample_conversations_cover_each_business_and_remove_cleanly(self):
        from backend.sample_conversations import remove_sample_conversations, seed_sample_conversations
        real = self.client.post('/api/conversations', json=dict(customer_name='Real customer', text='Pa-order po 1 cake')).json()
        with backend.connect() as db:
            self.assertEqual(seed_sample_conversations(db), 14)
            self.assertEqual(seed_sample_conversations(db), 0)
        conversations = self.client.get('/api/state').json()['conversations']
        samples = [c for c in conversations if c.get('is_sample')]
        self.assertEqual({k: sum(c['business_kind'] == k for c in samples) for k in ('bakery', 'gadgets', 'staycation', 'general')},
                         {'bakery': 4, 'gadgets': 4, 'staycation': 3, 'general': 3})
        for conversation in samples:
            self.assertFalse(conversation['is_demo'])
            self.assertEqual(conversation['version'], len(conversation['messages']))
            with backend.connect() as db:
                scoped, current = backend.extraction_scope(db, conversation)
            self.assertEqual(len(scoped['messages']), len(conversation['messages']))
            backend.extraction_request(scoped, self.client.get('/api/state').json()['all_products'], current)
        conversation = next(c for c in samples if c['business_kind'] == 'bakery')
        order = self.client.post('/api/orders', json=self.body(customer_name=conversation['customer_name'], customer_id=conversation['customer_id'])).json()
        with backend.connect() as db:
            self.assertEqual(remove_sample_conversations(db), 14)
        state = self.client.get('/api/state').json()
        ids = [c['id'] for c in state['conversations']]
        self.assertIn(real['id'], ids)
        self.assertFalse([key for key in ids if key.startswith('conv_sample_')])
        self.assertIn(order['id'], [o['id'] for o in state['orders']])
        self.assertIn(conversation['customer_id'], [c['id'] for c in state['customers']])

    def test_requested_live_sample_orders_are_labeled_and_seeded_once(self):
        from backend.sample_orders import seed_sample_orders
        with backend.connect() as db:
            before = {o['id']:o for o in backend.payloads(db, 'orders')}
            self.assertEqual(seed_sample_orders(db), 6)
            self.assertEqual(seed_sample_orders(db), 0)
            after = backend.payloads(db, 'orders')
            for order in after:
                if order['id'] in before:
                    self.assertEqual(order, before[order['id']])
                else:
                    self.assertTrue(order['is_sample'])
                    self.assertFalse(order['is_demo'])
                    self.assertEqual(order['payments'], [])
                    self.assertIn(order['business_kind'], ('gadgets','staycation'))
                    self.assertTrue(order['customer_name'].startswith('Sample · '))
            self.assertEqual(len({o['number'] for o in after}), len(after))

    def booking_body(self, **changes):
        self.client.put('/api/business', json={'kind':'staycation','name':'Stay'})
        body=self.body(items=[{'product_id':'p_staycation_starter_studio','quantity':99,'unit':'night'}],
                       reservation={'product_id':'p_staycation_starter_studio','check_in':'2026-11-01','check_out':'2026-11-03','guests':2,'status':'confirmed'},
                       due_date='2026-11-01')
        body.update(changes)
        return body

    def test_reservations_calculate_nights_and_reject_overlaps(self):
        body=self.booking_body()
        response=self.client.post('/api/orders',json=body)
        self.assertEqual(response.status_code,200,response.text)
        first=response.json()
        self.assertEqual(first['items'][0]['quantity'],2)
        self.assertEqual(first['total_cents'],500000)
        self.assertEqual(first['fulfillment'],'preparing')
        self.assertEqual(self.client.post('/api/orders',json=body).status_code,409)
        status=self.client.get('/api/reservations/availability',params={'product_id':body['reservation']['product_id'],'check_in':'2026-11-02','check_out':'2026-11-04'}).json()
        self.assertFalse(status['available'])
        # Half-open stays allow a new guest to arrive on the preceding guest's checkout date.
        adjacent=dict(body,reservation=dict(body['reservation'],check_in='2026-11-03',check_out='2026-11-04'))
        self.assertEqual(self.client.post('/api/orders',json=adjacent).status_code,200)
        different=dict(body,items=[{'product_id':'p_staycation_starter_family','quantity':1,'unit':'night'}],reservation=dict(body['reservation'],product_id='p_staycation_starter_family'))
        self.assertEqual(self.client.post('/api/orders',json=different).status_code,200)
        self.advance(first,'cancel')
        self.assertEqual(self.client.post('/api/orders',json=body).status_code,200)

    def test_pending_booking_checks_availability_at_confirmation_and_completion(self):
        body=self.booking_body()
        pending=self.client.post('/api/orders',json=dict(body,reservation=dict(body['reservation'],status='pending'))).json()
        first=self.client.post('/api/orders',json=body).json()
        response=self.client.post('/api/orders/'+pending['id']+'/transition',json={'action':'preparing','version':pending['version']})
        self.assertEqual(response.status_code,409)
        checked_in=self.advance(first,'ready')
        self.assertEqual(checked_in['reservation']['status'],'checked_in')
        completed=self.advance(checked_in,'fulfilled')
        self.assertEqual(completed['reservation']['status'],'completed')
        confirmed=self.advance(pending,'preparing')
        self.assertEqual(confirmed['reservation']['status'],'confirmed')
        update=dict(body,version=confirmed['version'],reservation=dict(body['reservation'],guests=3))
        self.assertEqual(self.client.put('/api/orders/'+confirmed['id'],json=update).status_code,200)

    def test_invalid_booking_dates_guests_and_missing_booking_rejected(self):
        body=self.booking_body()
        for reservation in [dict(body['reservation'],check_out='2026-11-01'),dict(body['reservation'],check_in='invalid'),dict(body['reservation'],guests=0)]:
            self.assertIn(self.client.post('/api/orders',json=dict(body,reservation=reservation)).status_code,(400,422))
        self.assertEqual(self.client.post('/api/orders',json=dict(body,reservation=None)).status_code,400)

    def test_business_specific_details_survive_revisions_and_fulfillment(self):
        for kind, field, value, product in [('bakery','packaging','Two gift boxes','p_pandesal'),('gadgets','variant','Blue 128GB','p_gadgets_starter_phone'),('general','service_location','Customer office','p_general_starter_service')]:
            self.client.put('/api/business',json={'kind':kind,'name':'Test'})
            unit='piece' if kind=='bakery' else 'unit' if kind=='gadgets' else 'service'
            body=self.body(items=[{'product_id':product,'quantity':1,'unit':unit}],**{field:value})
            response=self.client.post('/api/orders',json=body)
            self.assertEqual(response.status_code,200,response.text)
            order=response.json()
            self.assertEqual(order[field],value)
            revised=self.client.put('/api/orders/'+order['id'],json=dict(body,version=order['version'])).json()
            for action in ('preparing','ready','fulfilled'):
                revised=self.advance(revised,action)
            self.assertEqual(revised[field],value)
            self.assertEqual(revised['fulfillment'],'fulfilled')

    def test_simultaneous_booking_confirmations_reserve_only_one_unit(self):
        from concurrent.futures import ThreadPoolExecutor
        from fastapi import HTTPException
        body=self.booking_body()
        def reserve():
            try:
                backend.save_order(backend.OrderBody(**body))
                return 200
            except HTTPException as error:
                return error.status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sorted(pool.map(lambda _:reserve(),range(2))), [200,409])

    def test_local_booking_drafts_require_dates_and_remain_pending(self):
        self.client.put('/api/business',json={'kind':'staycation','name':'Stay'})
        conv={'messages':[{'id':'booking_message','text':'Studio stay for 2 guests November 1 to November 3, 2026, arrive 2pm.','created_at':backend.now()}]}
        proposal=dict(action='new_order',items=[{'product_id':'p_staycation_starter_studio','quantity':99,'unit':'night'}],due_date='2026-11-01',due_time='14:00',method='pickup',address='',notes='',questions=[],evidence=[{'message_id':'booking_message','quote':conv['messages'][0]['text']}])
        with backend.connect() as db:
            missing=backend.validate_proposal(db,dict(proposal,questions=[]),conv)
            self.assertEqual(missing['action'],'needs_clarification')
            complete=backend.validate_proposal(db,dict(proposal,questions=[],reservation={'product_id':'p_staycation_starter_studio','check_in':'2026-11-01','check_out':'2026-11-03','guests':2,'status':'confirmed'}),conv)
            self.assertEqual(complete['items'][0]['quantity'],2)
            self.assertEqual(complete['reservation']['status'],'pending')

    def test_extraction_output_is_bounded_and_context_has_no_payment_history(self):
        conv={'messages':[{'id':'bounded_message','text':'2 cookies please','created_at':backend.now()}]}
        current={'id':'existing','items':[], 'due_date':backend.today(),'due_time':'09:00','method':'pickup','address':'Known address','notes':'','payments':[{'id':'sensitive-payment-history'}],'customer_name':'Private name','version':99}
        with backend.connect() as db:
            products=backend.payloads(db,'products')
        _,request=backend.extraction_request(conv,products,current)
        schema=request['response_format']['json_schema']['schema'] if 'response_format' in request else request['format']
        fields=schema['properties']
        self.assertEqual(fields['questions']['maxItems'],4)
        self.assertEqual(fields['evidence']['maxItems'],6)
        self.assertEqual(fields['notes']['maxLength'],400)
        self.assertEqual(fields['evidence']['items']['properties']['message_id']['enum'],['bounded_message'])
        self.assertIn('p_cookie',fields['items']['items']['properties']['product_id']['enum'])
        context=json.loads(request['messages'][1]['content'])
        self.assertNotIn('payments',context['current_approved_order'])
        self.assertNotIn('customer_name',context['current_approved_order'])
        self.assertEqual(context['current_approved_order']['address'],'Known address')

    def test_extraction_retains_conversation_business_when_selected_theme_changes(self):
        self.client.put('/api/business',json={'kind':'gadgets','name':'Shop'})
        conv={'business_kind':'bakery','messages':[{'id':'m','text':'2 cookies','created_at':backend.now()}]}
        with backend.connect() as db:products=backend.payloads(db,'products')
        _,request=backend.extraction_request(conv,products,None)
        context=json.loads(request['messages'][1]['content'])
        self.assertEqual(context['business']['kind'],'bakery')
        self.assertIn('p_cookie',[p['id'] for p in context['catalog']])
        self.assertNotIn('p_gadgets_starter_phone',[p['id'] for p in context['catalog']])

    def test_explicit_separate_purchase_cannot_be_generated_as_an_open_order_revision(self):
        conv={'messages':[{'id':'separate','text':'Separate order po: 2 cookies','created_at':backend.now()}]}
        with backend.connect() as db:products=backend.payloads(db,'products')
        for current in (None,{'id':'existing','items':[]}):
            _,request=backend.extraction_request(conv,products,current)
            fields=(request['response_format']['json_schema']['schema'] if 'response_format' in request else request['format'])['properties']
            if current:
                self.assertEqual(fields['action']['enum'],['needs_clarification'])
                self.assertEqual(fields['items']['maxItems'],0)
                self.assertEqual(fields['questions']['minItems'],1)
            else:
                self.assertIn('new_order',fields['action']['enum'])
                self.assertGreater(fields['items']['maxItems'],0)

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

    def test_no_sign_in_but_cross_site_mutations_are_rejected(self):
        with TestClient(backend.app) as visitor:
            self.assertEqual(visitor.get('/api/state').status_code, 200)
        self.assertEqual(self.client.post('/api/orders', json=self.body(), headers={'origin':'https://other.example'}).status_code, 403)
        self.assertEqual(self.client.post('/api/orders', content=json.dumps(self.body()), headers={'content-type':'text/plain'}).status_code, 403)
        self.assertEqual(self.client.get('/api/auth/status').status_code, 404)

    def test_old_sign_in_tables_are_dropped_and_business_name_kept(self):
        with backend.connect() as db:
            db.execute("DELETE FROM settings WHERE key='business_profile'")
            db.execute('CREATE TABLE auth_owner (id INTEGER PRIMARY KEY CHECK(id=1),email TEXT NOT NULL,bakery_name TEXT NOT NULL,salt TEXT NOT NULL,password_hash TEXT NOT NULL)')
            db.execute("INSERT INTO auth_owner VALUES (1,'owner@example.test','Old bakery','00','00')")
            db.execute('CREATE TABLE auth_sessions (token_hash TEXT PRIMARY KEY,expires_at INTEGER NOT NULL)')
        backend.init_db()
        with backend.connect() as db:
            tables = {r['name'] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertFalse({'auth_owner', 'auth_sessions'} & tables)
        self.assertEqual(self.client.get('/api/state').json()['business'], {'kind': 'bakery', 'name': 'Old bakery'})

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

    def test_deleting_demo_orders_does_not_reuse_a_live_order_number(self):
        first = self.create()
        second = self.create()
        with backend.connect() as db:
            db.execute('DELETE FROM orders WHERE id=?', (first['id'],))
        third = self.create()
        self.assertEqual(int(third['number'][3:]), int(second['number'][3:]) + 1)

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

    def test_repeated_model_product_requires_quantity_review_without_doubling(self):
        for quantity in (3, 7):
            proposal=self.proposal()
            first=dict(proposal['items'][0])
            proposal['items'].append(dict(first,quantity=quantity))
            with backend.connect() as db:
                conv=backend.read_payload(db,'conversations','conv_demo')
                result=backend.validate_proposal(db,proposal,conv)
            self.assertEqual(result['action'],'needs_clarification')
            self.assertEqual(result['items'],[first])
            self.assertTrue(any('total quantity' in q for q in result['questions']))

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

    def approve_demo_request(self):
        with patch.object(backend.WORKER, 'submit'):
            job = self.client.post('/api/conversations/conv_demo/analyze', json={}).json()
        with backend.connect() as db:
            job.update(status='ready', proposal=self.proposal())
            backend.write_payload(db, 'jobs', job)
        order = self.client.post('/api/orders', json=self.body(job_id=job['id']))
        self.assertEqual(order.status_code, 200, order.text)
        return order.json()

    def test_approved_messages_are_not_extracted_again_and_revision_uses_new_message(self):
        order = self.approve_demo_request()
        self.assertEqual(self.client.post('/api/conversations/conv_demo/analyze', json={}).status_code, 409)
        conv = self.client.post('/api/conversations', json=dict(customer_name='Mika', conversation_id='conv_demo', text='Gawin na lang 4 dozen, same schedule.')).json()
        with backend.connect() as db:
            scoped, current = backend.extraction_scope(db, conv)
            self.assertEqual([m['text'] for m in scoped['messages']], ['Gawin na lang 4 dozen, same schedule.'])
            self.assertEqual(current['id'], order['id'])
            self.assertEqual(current['items'][0]['base_quantity'], 36)

    def test_completed_order_is_not_sent_as_context_for_next_purchase(self):
        order = self.approve_demo_request()
        self.advance(self.advance(self.advance(order, 'preparing'), 'ready'), 'fulfilled')
        conv = self.client.post('/api/conversations', json=dict(customer_name='Mika', conversation_id='conv_demo', text='3 cookies bukas 10am pickup')).json()
        with backend.connect() as db:
            scoped, current = backend.extraction_scope(db, conv)
            self.assertIsNone(current)
            self.assertEqual(len(scoped['messages']), 1)
            self.assertEqual(scoped['messages'][0]['text'], '3 cookies bukas 10am pickup')
            proposal = self.proposal()
            with self.assertRaisesRegex(ValueError, 'source message'):
                backend.validate_proposal(db, proposal, scoped)

    def test_legacy_approval_boundary_recovers_without_replaying_old_messages(self):
        self.approve_demo_request()
        with backend.connect() as db:
            conv = backend.read_payload(db, 'conversations', 'conv_demo')
            conv.pop('reviewed_message_count')
            backend.write_payload(db, 'conversations', conv)
            for job in backend.payloads(db, 'jobs'):
                job.pop('message_count', None)
                backend.write_payload(db, 'jobs', job)
        conv = self.client.post('/api/conversations', json=dict(customer_name='Mika', conversation_id='conv_demo', text='11am na lang po.')).json()
        with backend.connect() as db:
            scoped, _ = backend.extraction_scope(db, conv)
        self.assertEqual([m['text'] for m in scoped['messages']], ['11am na lang po.'])

    def test_explicit_new_purchase_preserves_open_order_and_customer(self):
        old = self.approve_demo_request()
        conv = self.client.post('/api/conversations', json=dict(customer_name='Mika', conversation_id='conv_demo', text='Separate order po, 3 cookies bukas 10am pickup')).json()
        with patch.object(backend.WORKER, 'submit'):
            response = self.client.post('/api/conversations/conv_demo/start-order', json=dict(message_id=conv['messages'][-1]['id'], version=conv['version']))
        self.assertEqual(response.status_code, 200, response.text)
        job = response.json()
        with backend.connect() as db:
            fresh = backend.read_payload(db, 'conversations', conv['id'])
            scoped, current = backend.extraction_scope(db, fresh)
            self.assertIsNone(current)
            self.assertEqual(len(scoped['messages']), 1)
            proposal = self.proposal()
            proposal.update(items=[dict(product_id='p_cookie', quantity=3, unit='piece')], evidence=[dict(message_id=conv['messages'][-1]['id'], quote='3 cookies')])
            job.update(status='ready', proposal=proposal)
            backend.write_payload(db, 'jobs', job)
        saved = self.client.post('/api/orders', json=self.body(job_id=job['id'], items=proposal['items']))
        self.assertEqual(saved.status_code, 200, saved.text)
        self.assertNotEqual(saved.json()['id'], old['id'])
        self.assertEqual(saved.json()['customer_id'], old['customer_id'])
        with backend.connect() as db:
            self.assertEqual(backend.enrich(backend.read_payload(db, 'orders', old['id'])), old)
        stale = self.client.post('/api/conversations/conv_demo/start-order', json=dict(message_id=conv['messages'][-1]['id'], version=conv['version']))
        self.assertEqual(stale.status_code, 409)

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

    def test_profile_enrichment_preserves_orders_and_serves_cached_photo_privately(self):
        order = self.create()
        with backend.connect() as db:
            customer = backend.read_payload(db, 'customers', order['customer_id'])
            customer.update(source='facebook', facebook_sender_id='12345')
            backend.write_payload(db, 'customers', customer)
        with tempfile.TemporaryDirectory() as photo_dir, patch.object(backend, 'DATA', Path(photo_dir)), patch.object(backend, 'fetch_profile', return_value=dict(status='available', name='Juan Santos', photo=b'cached-image', mime='image/jpeg')):
            backend.enrich_profile(customer['id'])
            state = self.client.get('/api/state').json()
            updated = next(o for o in state['orders'] if o['id'] == order['id'])
            self.assertEqual(updated['customer_name'], 'Juan Santos')
            self.assertEqual(updated['version'], order['version'])
            self.assertEqual(updated['items'], order['items'])
            updated_customer = next(c for c in state['customers'] if c['id'] == customer['id'])
            photo_url = updated_customer['profile_photo_url']
            self.assertEqual(self.client.get(photo_url).content, b'cached-image')
            with patch.object(backend, 'fetch_profile', return_value=dict(status='unavailable')):
                backend.enrich_profile(customer['id'])
            self.assertEqual(self.client.get(photo_url).content, b'cached-image')
            self.assertEqual(next(c for c in self.client.get('/api/state').json()['customers'] if c['id'] == customer['id'])['name'], 'Juan Santos')

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

    def edit_product(self, product_id, **changes):
        product = next(p for p in self.client.get('/api/state').json()['all_products'] if p['id'] == product_id)
        response = self.client.put('/api/products/' + product_id, json=dict(product, **changes))
        self.assertEqual(response.status_code, 200, response.text)

    def revise(self, order, **changes):
        return self.client.put('/api/orders/' + order['id'], json=self.body(version=order['version'], **changes))

    def test_revision_keeps_approved_price_and_status_for_unchanged_items(self):
        order = self.advance(self.advance(self.create(), 'preparing'), 'ready')
        self.edit_product('p_pandesal', price_cents=1500, name='Cheese pandesal (new)')
        revised = self.revise(order, due_time='10:00')
        self.assertEqual(revised.status_code, 200, revised.text)
        self.assertEqual(revised.json()['fulfillment'], 'ready')
        self.assertEqual(revised.json()['items'], order['items'])
        changed = self.revise(revised.json(), items=[dict(product_id='p_pandesal', quantity=4, unit='dozen')])
        self.assertEqual(changed.json()['total_cents'], 48 * 1500)
        self.assertEqual(changed.json()['fulfillment'], 'queued')

    def test_inactive_product_does_not_block_editing_other_order_details(self):
        order = self.create()
        self.edit_product('p_pandesal', active=False)
        self.assertEqual(self.revise(order, due_time='11:00').status_code, 200)
        latest = self.client.get('/api/state').json()['orders']
        order = next(o for o in latest if o['id'] == order['id'])
        self.assertEqual(self.revise(order, items=[dict(product_id='p_pandesal', quantity=4, unit='dozen')]).status_code, 400)

    def test_out_for_delivery_address_can_be_corrected_after_catalog_edit(self):
        order = self.create(method='delivery', address='Old St')
        order = self.advance(self.advance(self.advance(order, 'preparing'), 'ready'), 'out_for_delivery')
        self.edit_product('p_pandesal', price_cents=1500)
        revised = self.revise(order, method='delivery', address='New St')
        self.assertEqual(revised.status_code, 200, revised.text)
        self.assertEqual(revised.json()['fulfillment'], 'out_for_delivery')

    def test_message_burst_replaces_stale_extraction_instead_of_failing(self):
        def send(mid, text):
            raw = json.dumps(dict(object='page', entry=[dict(id='test_page', messaging=[dict(sender=dict(id='customer1'), message=dict(mid=mid, text=text))])])).encode()
            signature = 'sha256=' + hmac.new(b'test-secret', raw, hashlib.sha256).hexdigest()
            self.assertEqual(self.client.post('/api/facebook/webhook', content=raw, headers={'x-hub-signature-256': signature}).status_code, 200)
        with patch.dict(os.environ, META_APP_SECRET='test-secret', META_VERIFY_TOKEN='verify', META_PAGE_ID='test_page'), patch.object(backend.WORKER, 'submit'):
            send('message1', '2 dozen pandesal bukas')
            send('message2', '9am pickup po')
        jobs = self.client.get('/api/state').json()['jobs']
        self.assertEqual([j['status'] for j in jobs], ['canceled', 'queued'])
        self.assertEqual(jobs[1]['message_count'], 2)
        backend.run_job(jobs[0]['id'])
        self.assertEqual(self.client.get('/api/state').json()['jobs'][0]['status'], 'canceled')

    def test_webhook_saves_messages_even_if_extraction_cannot_be_queued(self):
        raw = json.dumps(dict(object='page', entry=[dict(id='test_page', messaging=[dict(sender=dict(id='customer1'), message=dict(mid='message1', text='hi'))])])).encode()
        signature = 'sha256=' + hmac.new(b'test-secret', raw, hashlib.sha256).hexdigest()
        with patch.dict(os.environ, META_APP_SECRET='test-secret', META_VERIFY_TOKEN='verify', META_PAGE_ID='test_page'), \
                patch.object(backend, 'analyze', side_effect=RuntimeError('queue failed')), self.assertLogs('bentabuddy', 'ERROR'):
            self.assertEqual(self.client.post('/api/facebook/webhook', content=raw, headers={'x-hub-signature-256': signature}).status_code, 200)
        self.assertTrue(any(c['source'] == 'facebook' for c in self.client.get('/api/state').json()['conversations']))

    def test_clarification_after_closed_order_can_be_confirmed_as_new_order(self):
        first = self.advance(self.advance(self.advance(self.create(), 'preparing'), 'ready'), 'fulfilled')
        with backend.connect() as db:
            conv = backend.read_payload(db, 'conversations', 'conv_demo')
            conv.update(linked_order_id=first['id'], customer_id=first['customer_id'], is_demo=False)
            backend.write_payload(db, 'conversations', conv)
        with patch.object(backend.WORKER, 'submit'):
            job = self.client.post('/api/conversations/conv_demo/analyze', json={}).json()
        with backend.connect() as db:
            job.update(status='ready', proposal=dict(self.proposal(), action='needs_clarification'))
            backend.write_payload(db, 'jobs', job)
        second = self.client.post('/api/orders', json=self.body(job_id=job['id']))
        self.assertEqual(second.status_code, 200, second.text)
        self.assertNotEqual(second.json()['id'], first['id'])

    def test_accommodation_must_be_priced_per_night(self):
        self.client.put('/api/business', json={'kind': 'staycation', 'name': 'Stay'})
        product = dict(name='Villa', category='Accommodations', price_cents=100000, unit='stay', offering_type='accommodation')
        self.assertEqual(self.client.post('/api/products', json=product).status_code, 400)
        self.assertEqual(self.client.post('/api/products', json=dict(product, unit='night')).status_code, 200)
        service = self.client.post('/api/products', json=dict(product, offering_type='service')).json()
        self.assertEqual(self.client.put('/api/products/' + service['id'], json=dict(service, offering_type='accommodation')).status_code, 400)


if __name__ == '__main__':
    unittest.main()
