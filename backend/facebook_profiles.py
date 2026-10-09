"""Optional Meta profile lookup. Never log tokens or expose remote photo URLs."""
from urllib.parse import urlparse

import httpx


def fetch_profile(sender, token, version='v22.0'):
    result = {'status': 'unavailable'}
    if not sender.isdigit() or not token:
        return {'status': 'unavailable'}
    try:
        with httpx.Client(timeout=10, follow_redirects=False) as client:
            response = client.get(
                'https://graph.facebook.com/' + version + '/' + sender,
                params={'fields': 'first_name,last_name,profile_pic'},
                headers={'Authorization': 'Bearer ' + token},
            )
            if response.status_code != 200:
                return {'status': 'unavailable'}
            data = response.json()
            if not isinstance(data, dict):
                return {'status': 'unavailable'}
            name = ' '.join(str(data.get(k) or '').strip() for k in ['first_name', 'last_name']).strip()[:100]
            result = {'status': 'available' if name else 'unavailable', 'name': name}
            photo = data.get('profile_pic')
            if not isinstance(photo, str):
                return result
            url = urlparse(photo)
            host = url.hostname or ''
            if url.scheme != 'https' or url.port not in (None, 443) or url.username or not any(
                host == domain or host.endswith('.' + domain)
                for domain in ['fbcdn.net', 'facebook.com', 'fbsbx.com']
            ):
                return result
            # Download a bounded image once so the browser can use it offline.
            with client.stream('GET', photo) as image:
                mime = image.headers.get('content-type', '').split(';')[0]
                if image.status_code != 200 or mime not in ['image/jpeg', 'image/png', 'image/webp']:
                    return result
                chunks, size = [], 0
                for chunk in image.iter_bytes():
                    size += len(chunk)
                    if size > 2_000_000:
                        return result
                    chunks.append(chunk)
                if size:
                    result.update(photo=b''.join(chunks), mime=mime)
            return result
    except (httpx.HTTPError, ValueError, TypeError):
        # A CDN failure must not discard a successfully fetched name.
        return result
