import unittest
from unittest.mock import patch

import httpx
from backend.facebook_profiles import fetch_profile


class FacebookProfiles(unittest.TestCase):
    def lookup(self, handler):
        client = httpx.Client(transport=httpx.MockTransport(handler))
        with patch('backend.facebook_profiles.httpx.Client', return_value=client):
            return fetch_profile('12345', 'private-token')

    def test_profile_and_bounded_photo_download_without_leaking_token_to_cdn(self):
        calls = []
        def handler(request):
            calls.append(request)
            if request.url.host == 'graph.facebook.com':
                self.assertEqual(request.headers['authorization'], 'Bearer private-token')
                self.assertNotIn('access_token', request.url.params)
                return httpx.Response(200, json=dict(first_name='Juan', last_name='Santos', profile_pic='https://scontent.fbcdn.net/photo'))
            self.assertNotIn('authorization', request.headers)
            return httpx.Response(200, content=b'photo', headers={'content-type': 'image/jpeg'})
        result = self.lookup(handler)
        self.assertEqual(result['name'], 'Juan Santos')
        self.assertEqual(result['photo'], b'photo')
        self.assertEqual(len(calls), 2)

    def test_untrusted_image_host_is_never_requested(self):
        calls = []
        def handler(request):
            calls.append(request)
            return httpx.Response(200, json=dict(first_name='Juan', profile_pic='https://127.0.0.1/private'))
        self.assertEqual(self.lookup(handler)['name'], 'Juan')
        self.assertEqual(len(calls), 1)

    def test_permission_denied_is_a_fallback(self):
        self.assertEqual(self.lookup(lambda request: httpx.Response(403, json={'error': {'message': 'denied'}})), {'status': 'unavailable'})

    def test_oversized_photo_keeps_name_without_caching_image(self):
        def handler(request):
            if request.url.host == 'graph.facebook.com':
                return httpx.Response(200, json=dict(first_name='Juan', profile_pic='https://scontent.fbcdn.net/photo'))
            return httpx.Response(200, content=b'x' * 2_000_001, headers={'content-type': 'image/jpeg'})
        result = self.lookup(handler)
        self.assertEqual(result['name'], 'Juan')
        self.assertNotIn('photo', result)
