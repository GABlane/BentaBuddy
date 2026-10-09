"""Request guard for the local demo. There is no sign-in; this only blocks cross-site writes."""
from fastapi import Request
from fastapi.responses import JSONResponse


def install_guard(app):
    @app.middleware('http')
    async def same_origin_writes(request: Request, call_next):
        path = request.url.path
        if path.startswith('/api/') and path != '/api/facebook/webhook' and request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            # Cross-site forms cannot send JSON. Also reject cross-origin fetches.
            origin = request.headers.get('origin')
            expected_origin = str(request.base_url).rstrip('/')
            if (origin and origin != expected_origin) or request.headers.get('content-type', '').split(';')[0] != 'application/json':
                return JSONResponse({'detail': 'Please submit from the BentaBuddy website.'}, status_code=403)
        response = await call_next(request)
        if path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response
