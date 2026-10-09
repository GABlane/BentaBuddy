import unittest
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient
from backend.facebook_relay import app


class FacebookRelay(unittest.TestCase):
    def test_dashboard_and_auth_are_not_public(self):
        with TestClient(app) as visitor, patch('backend.facebook_relay.httpx.AsyncClient') as upstream:
            for path in ['/', '/api/state', '/api/auth/status', '/docs', '/openapi.json']:
                self.assertEqual(visitor.get(path).status_code, 404)
            self.assertEqual(visitor.post('/api/orders', json={}).status_code, 404)
            upstream.assert_not_called()

    def test_signed_payload_is_forwarded_byte_for_byte_without_cookies(self):
        raw = b'{ "object": "page", "entry": [] }\n'
        with TestClient(app) as visitor, patch('backend.facebook_relay.httpx.AsyncClient') as factory:
            upstream = factory.return_value.__aenter__.return_value
            upstream.request = AsyncMock(return_value=httpx.Response(403, content=b'{"detail":"Invalid signature"}', headers={'content-type':'application/json'}))
            response = visitor.post('/api/facebook/webhook', content=raw, headers={'content-type':'application/json','x-hub-signature-256':'sha256=test','cookie':'private=value'})
            self.assertEqual(response.status_code, 403)
            self.assertEqual(response.json()['detail'], 'Invalid signature')
            args = upstream.request.await_args
            self.assertEqual(args.args, ('POST', 'http://127.0.0.1:8000/api/facebook/webhook'))
            self.assertEqual(args.kwargs['content'], raw)
            self.assertEqual(args.kwargs['headers']['x-hub-signature-256'], 'sha256=test')
            self.assertNotIn('cookie', args.kwargs['headers'])

    def test_verification_challenge_and_query_are_preserved(self):
        with TestClient(app) as visitor, patch('backend.facebook_relay.httpx.AsyncClient') as factory:
            upstream = factory.return_value.__aenter__.return_value
            upstream.request = AsyncMock(return_value=httpx.Response(200, content=b'challenge-123', headers={'content-type':'text/plain'}))
            response = visitor.get('/api/facebook/webhook', params={'hub.mode':'subscribe','hub.verify_token':'synthetic-token','hub.challenge':'challenge-123'})
            self.assertEqual(response.text, 'challenge-123')
            self.assertEqual(dict(upstream.request.await_args.kwargs['params'])['hub.verify_token'], 'synthetic-token')
            self.assertEqual(response.headers['cache-control'], 'no-store')

    def test_unavailable_backend_and_large_payload_fail_cleanly(self):
        with TestClient(app) as visitor, patch('backend.facebook_relay.httpx.AsyncClient') as factory:
            upstream = factory.return_value.__aenter__.return_value
            upstream.request = AsyncMock(side_effect=httpx.ConnectError('offline'))
            self.assertEqual(visitor.get('/api/facebook/webhook').status_code, 502)
            upstream.request.reset_mock()
            self.assertEqual(visitor.post('/api/facebook/webhook', content=b'x' * 1000001).status_code, 413)
            upstream.request.assert_not_awaited()
