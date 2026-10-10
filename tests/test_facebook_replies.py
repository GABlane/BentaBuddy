"""Outbound Messenger behavior with isolated data and mocked network calls."""
import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

_BOOT = tempfile.TemporaryDirectory()
os.environ.setdefault('BENTABUDDY_DATA', _BOOT.name)
from backend import app as backend
from backend.facebook_replies import send_acknowledgment


class AutoReplies(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.original_db = backend.DB
        backend.DB = Path(self.directory.name) / 'test.sqlite3'
        backend.init_db()
        self.stack = ExitStack()
        self.stack.enter_context(patch.dict(os.environ, META_APP_SECRET='test-secret', META_PAGE_ID='123', META_PAGE_ACCESS_TOKEN='private-test-token'))
        self.submit = self.stack.enter_context(patch.object(backend.REPLY_WORKER, 'submit'))
        self.stack.enter_context(patch.object(backend, 'queue_profile'))
        self.stack.enter_context(patch.object(backend, 'analyze'))
        self.client = TestClient(backend.app)

    def tearDown(self):
        self.client.close()
        self.stack.close()
        backend.DB = self.original_db
        self.directory.cleanup()

    def send(self, mid='m1', sender='456', page='123', stamp=None, echo=False, valid=True):
        raw = json.dumps({'object':'page','entry':[{'id':page,'messaging':[{
            'sender':{'id':sender},'timestamp':int(time.time()*1000) if stamp is None else stamp,
            'message':{'mid':mid,'text':'2 cookies bukas please','is_echo':echo},
        }]}]}).encode()
        signature = 'sha256=' + hmac.new(b'test-secret', raw, hashlib.sha256).hexdigest()
        return self.client.post('/api/facebook/webhook',content=raw,headers={'x-hub-signature-256':signature if valid else 'bad'})

    def enable(self, **options):
        response = self.client.put('/api/facebook/auto-reply',json={'enabled':True,**options})
        self.assertEqual(response.status_code,200,response.text)

    def records(self):
        with backend.connect() as db:
            return backend.payloads(db,'facebook_replies')

    def test_off_by_default_and_requires_configured_token_to_enable(self):
        self.assertFalse(self.client.get('/api/facebook/auto-reply').json()['enabled'])
        self.assertEqual(self.send().status_code,200)
        self.assertEqual(self.records(),[])
        self.submit.assert_not_called()
        with patch.dict(os.environ,META_PAGE_ACCESS_TOKEN=''):
            self.assertEqual(self.client.put('/api/facebook/auto-reply',json={'enabled':True}).status_code,400)

    def test_duplicate_delivery_and_burst_only_queue_one_receipt(self):
        self.enable()
        for mid in ['m1','m1','m2']:
            self.assertEqual(self.send(mid).status_code,200)
        self.assertEqual(len(self.records()),1)
        self.submit.assert_called_once()
        state=self.client.get('/api/state').json()
        self.assertEqual(len(state['conversations'][0]['messages']),2)
        self.assertEqual(state['orders'],[])
        reply=self.records()[0]
        self.assertIn('Hindi pa confirmed',reply['text'])
        public=self.client.get('/api/facebook/auto-reply').text
        self.assertNotIn('private-test-token',public)
        self.assertNotIn('sender_id',public)

    def test_bad_signature_wrong_page_echo_old_or_missing_time_never_reply(self):
        self.enable()
        self.assertEqual(self.send(valid=False).status_code,403)
        self.send(mid='wrongpage',page='999')
        self.send(mid='echo',echo=True)
        self.send(mid='old',stamp=int((time.time()-86401)*1000))
        self.send(mid='missing',stamp=0)
        self.send(mid='future',stamp=int((time.time()+120)*1000))
        self.assertEqual(self.records(),[])
        self.submit.assert_not_called()

    def test_delivered_once_and_outbound_text_never_enters_extraction(self):
        self.enable()
        self.send()
        reply=self.records()[0]
        with patch.object(backend,'send_acknowledgment',return_value={'status':'sent','message_id':'outbound'}) as transport:
            backend.deliver_acknowledgment(reply['id'])
            backend.deliver_acknowledgment(reply['id'])
        transport.assert_called_once()
        self.assertEqual(self.records()[0]['status'],'sent')
        self.assertEqual(len(self.client.get('/api/state').json()['conversations'][0]['messages']),1)

    def test_disable_or_expired_window_skips_pending_reply(self):
        self.enable()
        self.send()
        reply=self.records()[0]
        self.client.put('/api/facebook/auto-reply',json={'enabled':False})
        with patch.object(backend,'send_acknowledgment') as transport:
            backend.deliver_acknowledgment(reply['id'])
        transport.assert_not_called()
        self.assertEqual(self.records()[0]['status'],'skipped')
        self.enable()
        self.send(mid='m2',sender='789')
        reply=self.records()[-1]
        with backend.connect() as db:
            reply['source_time']=(backend.datetime.now(backend.TZ)-timedelta(hours=25)).isoformat()
            backend.write_payload(db,'facebook_replies',reply)
        with patch.object(backend,'send_acknowledgment') as transport:
            backend.deliver_acknowledgment(reply['id'])
        transport.assert_not_called()
        self.assertEqual(self.records()[-1]['status'],'skipped')

    def test_cooldown_expires_and_different_customers_are_independent(self):
        self.enable()
        self.send()
        self.send(mid='m2',sender='789')
        self.assertEqual(len(self.records()),2)
        with backend.connect() as db:
            reply=self.records()[0]
            reply['created_at']=(backend.datetime.now(backend.TZ)-timedelta(minutes=16)).isoformat()
            backend.write_payload(db,'facebook_replies',reply)
        self.send(mid='m3')
        self.assertEqual(len(self.records()),3)

    def test_failure_and_restart_do_not_retry_uncertain_sends(self):
        self.enable()
        self.send()
        reply=self.records()[0]
        with patch.object(backend,'send_acknowledgment',return_value={'status':'failed','error':'Delivery unconfirmed'}) as transport:
            backend.deliver_acknowledgment(reply['id'])
            backend.deliver_acknowledgment(reply['id'])
        transport.assert_called_once()
        self.send(mid='m2')
        self.assertEqual(len(self.records()),1)
        with backend.connect() as db:
            reply=self.records()[0]
            reply['status']='sending'
            backend.write_payload(db,'facebook_replies',reply)
        backend.init_db()
        self.assertEqual(self.records()[0]['status'],'failed')
        self.assertIn('No automatic retry',self.records()[0]['error'])
        self.assertTrue(self.client.get('/api/facebook/auto-reply').json()['enabled'])

    def test_concurrent_workers_claim_the_send_only_once(self):
        self.enable()
        self.send()
        reply=self.records()[0]
        with patch.object(backend,'send_acknowledgment',return_value={'status':'sent','message_id':'outbound'}) as transport:
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(backend.deliver_acknowledgment,[reply['id'],reply['id']]))
        transport.assert_called_once()

    def test_queue_failure_does_not_fail_message_receipt_or_retry(self):
        self.enable()
        self.submit.side_effect=RuntimeError('queue stopped')
        self.assertEqual(self.send().status_code,200)
        self.assertEqual(self.records()[0]['status'],'failed')
        self.assertEqual(self.send().status_code,200)
        self.submit.assert_called_once()
        self.assertEqual(len(self.client.get('/api/state').json()['conversations'][0]['messages']),1)

    def test_page_change_cancels_pending_reply(self):
        self.enable()
        self.send()
        with patch.dict(os.environ,META_PAGE_ID='999'),patch.object(backend,'send_acknowledgment') as transport:
            backend.deliver_acknowledgment(self.records()[0]['id'])
        transport.assert_not_called()
        self.assertEqual(self.records()[0]['status'],'skipped')

    def make_order(self, **changes):
        conv=self.client.get('/api/state').json()['conversations'][0]
        values=dict(customer_name=conv['customer_name'],customer_id=conv['customer_id'],items=[{'product_id':'p_cookie','quantity':2,'unit':'piece'}],due_date=backend.today(),due_time='10:00',method='pickup')
        values.update(changes)
        return backend.save_order(backend.OrderBody(**values))

    def test_ai_preview_only_receives_own_orders_and_never_sends(self):
        self.send()
        own=self.make_order()
        other=backend.save_order(backend.OrderBody(customer_name='Other buyer',items=[{'product_id':'p_cake','quantity':1,'unit':'cake'}],due_date=backend.today(),due_time='12:00',method='pickup'))
        conv=self.client.get('/api/state').json()['conversations'][0]
        response=httpx.Response(200,request=httpx.Request('POST','http://127.0.0.1:11434/v1/chat/completions'),json={'choices':[{'finish_reason':'stop','message':{'content':json.dumps({'reply_id':'status:'+own['id']})}}]})
        with patch.object(backend.httpx,'post',return_value=response) as model,patch.object(backend,'send_acknowledgment') as send:
            result=self.client.post('/api/facebook/reply-preview',json={'conversation_id':conv['id'],'text':'Status po ng '+own['number']}).json()
        self.assertIn(own['number'],result['text'])
        context=json.loads(model.call_args.kwargs['json']['messages'][1]['content'])
        self.assertEqual([o['id'] for o in context['orders']],[own['id']])
        self.assertNotIn(other['id'],str(context))
        self.assertTrue(model.call_args.args[0].startswith('http://127.0.0.1:11434/'))
        send.assert_not_called()

    def test_unknown_model_order_id_uses_safe_fallback(self):
        self.send()
        own=self.make_order()
        response=httpx.Response(200,request=httpx.Request('POST','http://127.0.0.1:11434/v1/chat/completions'),json={'choices':[{'message':{'content':'{"reply_id":"status:another_customer"}'}}]})
        with patch.object(backend.httpx,'post',return_value=response):
            result=backend.customer_answer('Status?', [own])
        self.assertEqual(result['reply_source'],'fallback')
        self.assertNotIn('another_customer',result['text'])

    def test_ai_reply_uses_latest_status_after_generation(self):
        self.send()
        own=self.make_order()
        self.enable(ai_enabled=True)
        self.send(mid='status')
        reply=self.records()[-1]
        self.assertEqual(reply['kind'],'ai_reply')
        def answer(*_):
            backend.transition(own['id'],backend.TransitionBody(action='preparing',version=own['version']))
            return {'text':'invented model prose is never used for status','reply_id':'status:'+own['id'],'reply_source':'local_ai'}
        with patch.object(backend,'customer_answer',side_effect=answer),patch.object(backend,'send_acknowledgment',return_value={'status':'sent','message_id':'out'}) as send:
            backend.deliver_acknowledgment(reply['id'])
        self.assertIn('inihahanda sa kitchen',send.call_args.args[2])
        self.assertNotIn('invented',send.call_args.args[2])

    def test_followup_replaces_unfinished_ai_reply(self):
        self.enable(ai_enabled=True)
        self.send()
        reply=self.records()[0]
        def answer(*_):
            self.send(mid='followup')
            return {'text':'old reply','reply_id':'clarify','reply_source':'local_ai'}
        with patch.object(backend,'customer_answer',side_effect=answer),patch.object(backend,'send_acknowledgment') as send:
            backend.deliver_acknowledgment(reply['id'])
        send.assert_not_called()
        self.assertEqual(self.records()[0]['status'],'skipped')
        self.assertEqual(self.records()[-1]['status'],'queued')

    def test_disabling_ai_during_generation_prevents_send(self):
        self.enable(ai_enabled=True)
        self.send()
        reply=self.records()[0]
        def answer(*_):
            backend.update_auto_reply(backend.AutoReplyBody(enabled=True,ai_enabled=False))
            return {'text':'unused','reply_id':'receipt','reply_source':'local_ai'}
        with patch.object(backend,'customer_answer',side_effect=answer),patch.object(backend,'send_acknowledgment') as send:
            backend.deliver_acknowledgment(reply['id'])
        send.assert_not_called()
        self.assertEqual(self.records()[0]['status'],'skipped')

    def test_owner_changes_queue_status_updates_and_skip_outdated_versions(self):
        self.send()
        self.enable(status_updates=True)
        own=self.make_order()
        backend.queue_order_status(own)
        preparing=backend.transition(own['id'],backend.TransitionBody(action='preparing',version=own['version']))
        backend.transition(own['id'],backend.TransitionBody(action='ready',version=preparing['version']))
        updates=[r for r in self.records() if r.get('kind')=='status_update']
        self.assertEqual(len(updates),3)
        with patch.object(backend,'send_acknowledgment',return_value={'status':'sent','message_id':'out'}) as send:
            for update in updates:
                backend.deliver_acknowledgment(update['id'])
        send.assert_called_once()
        self.assertIn('pickup',send.call_args.args[2])
        self.assertEqual([r['status'] for r in self.records()],['skipped','skipped','sent'])

    def test_expired_window_does_not_prevent_owner_status_change(self):
        self.send(stamp=int((time.time()-90000)*1000))
        self.enable(status_updates=True)
        own=self.make_order()
        preparing=backend.transition(own['id'],backend.TransitionBody(action='preparing',version=own['version']))
        self.assertEqual(preparing['fulfillment'],'preparing')
        self.assertEqual(self.records(),[])

    def test_booking_notifications_follow_owner_confirm_checkin_checkout(self):
        from backend.business import ensure_catalog
        self.send()
        self.enable(status_updates=True)
        with backend.connect() as db:
            ensure_catalog(db,'staycation')
            db.execute("INSERT OR REPLACE INTO settings VALUES ('business_profile',?)",(json.dumps({'kind':'staycation','name':'Test stay'}),))
            product=backend.read_payload(db,'products','p_staycation_starter_studio')
            product.update(available=True,price_cents=150000)
            backend.write_payload(db,'products',product)
        order=self.make_order(items=[{'product_id':product['id'],'quantity':2,'unit':'night'}],reservation={'product_id':product['id'],'check_in':'2026-11-20','check_out':'2026-11-22','guests':2,'status':'pending'})
        with patch.object(backend,'send_acknowledgment',return_value={'status':'sent','message_id':'out'}) as send:
            backend.deliver_acknowledgment(self.records()[-1]['id'])
            self.assertIn('hindi pa confirmed',send.call_args.args[2])
            for action,word in [('preparing','Confirmed na'),('ready','checked in'),('fulfilled','completed')]:
                order=backend.transition(order['id'],backend.TransitionBody(action=action,version=order['version']))
                backend.deliver_acknowledgment(self.records()[-1]['id'])
                self.assertIn(word,send.call_args.args[2])
        self.assertEqual(send.call_count,4)

    def test_unavailable_model_returns_safe_receipt(self):
        with patch.object(backend.httpx,'post',side_effect=httpx.ConnectError('offline')):
            result=backend.customer_answer('Status po?',[])
        self.assertEqual(result['reply_source'],'fallback')
        self.assertNotIn('Confirmed na',result['text'])

    def test_old_settings_client_preserves_new_reply_modes(self):
        self.enable(ai_enabled=True,status_updates=True)
        result=self.client.put('/api/facebook/auto-reply',json={'enabled':False}).json()
        self.assertFalse(result['enabled'])
        self.assertTrue(result['ai_enabled'])
        self.assertTrue(result['status_updates'])


class SendTransport(unittest.TestCase):
    def test_request_uses_bearer_token_and_response_type(self):
        response=httpx.Response(200,json={'message_id':'outbound1'})
        with patch('backend.facebook_replies.httpx.post',return_value=response) as post:
            result=send_acknowledgment('123','456','Receipt only','secret-token','v22.0')
        self.assertEqual(result,{'status':'sent','message_id':'outbound1'})
        self.assertEqual(post.call_args.args[0],'https://graph.facebook.com/v22.0/123/messages')
        self.assertEqual(post.call_args.kwargs['headers']['Authorization'],'Bearer secret-token')
        self.assertEqual(post.call_args.kwargs['json'],{'recipient':{'id':'456'},'messaging_type':'RESPONSE','message':{'text':'Receipt only'}})
        self.assertFalse(post.call_args.kwargs['follow_redirects'])

    def test_denied_timeout_and_malformed_response_do_not_leak_tokens(self):
        for response in [httpx.Response(403,text='secret-token'),httpx.Response(200,text='not json'),httpx.Response(200,json={})]:
            with patch('backend.facebook_replies.httpx.post',return_value=response):
                result=send_acknowledgment('123','456','Receipt','secret-token','v22.0')
            self.assertEqual(result['status'],'failed')
            self.assertNotIn('secret-token',str(result))
        with patch('backend.facebook_replies.httpx.post',side_effect=httpx.ReadTimeout('secret-token')):
            result=send_acknowledgment('123','456','Receipt','secret-token','v22.0')
        self.assertEqual(result['status'],'failed')
        self.assertNotIn('secret-token',str(result))

    def test_invalid_identifiers_or_version_never_contact_meta(self):
        with patch('backend.facebook_replies.httpx.post') as post:
            for args in [('123','bad','Text','token','v22.0'),('123','456','Text','token','bad/version'),('123','456','Text','','v22.0')]:
                self.assertEqual(send_acknowledgment(*args)['status'],'failed')
        post.assert_not_called()
