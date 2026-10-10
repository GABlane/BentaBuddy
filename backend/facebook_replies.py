"""Messenger transport for receipts and grounded status replies; no automatic retries."""
import re

import httpx


ACKNOWLEDGMENT = ('Salamat po! Natanggap namin ang message ninyo. Ire-review muna ito ng '
                 '{business}. Hindi pa confirmed ang order o booking; maghintay po ng confirmation mula sa shop.')
COOLDOWN_SECONDS = 15 * 60
WINDOW_SECONDS = 24 * 60 * 60


def send_acknowledgment(page, sender, text, token, version):
    if not page.isdigit() or not sender.isdigit() or not token or not re.fullmatch(r'v\d+\.\d+', version):
        return {'status': 'failed', 'error': 'Check the Page ID, Page token, and Graph API version.'}
    try:
        response = httpx.post(
            'https://graph.facebook.com/' + version + '/' + page + '/messages',
            headers={'Authorization': 'Bearer ' + token},
            json={'recipient': {'id': sender}, 'messaging_type': 'RESPONSE', 'message': {'text': text}},
            timeout=10, follow_redirects=False,
        )
        if response.status_code != 200:
            # Never return/log remote error bodies: they can include credentials.
            return {'status': 'failed', 'error': 'Meta rejected the reply. Check Page token, messaging permission, and recipient access.'}
        data = response.json()
        if not isinstance(data, dict) or not data.get('message_id'):
            return {'status': 'failed', 'error': 'Delivery could not be confirmed. No automatic retry was made.'}
        return {'status': 'sent', 'message_id': str(data['message_id'])}
    except (httpx.HTTPError, ValueError):
        return {'status': 'failed', 'error': 'Delivery could not be confirmed. Check internet/Meta before sending manually; no automatic retry was made.'}
