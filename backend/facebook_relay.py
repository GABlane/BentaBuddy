"""Public-facing relay exposing only the signed Messenger webhook, never the dashboard."""
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
BACKEND = 'http://127.0.0.1:8000/api/facebook/webhook'


@app.api_route('/api/facebook/webhook', methods=['GET', 'POST'])
async def relay(request: Request):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 1000000:
            return JSONResponse({'detail': 'Payload too large'}, status_code=413)
    headers = {name: request.headers[name] for name in ['content-type', 'x-hub-signature-256'] if name in request.headers}
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
            response = await client.request(request.method, BACKEND, params=list(request.query_params.multi_items()), content=bytes(raw), headers=headers)
    except httpx.HTTPError:
        return JSONResponse({'detail': 'Local bakery server unavailable. Keep BentaBuddy running.'}, status_code=502)
    return Response(content=response.content, status_code=response.status_code, headers={'content-type': response.headers.get('content-type', 'application/json'), 'cache-control': 'no-store'})
