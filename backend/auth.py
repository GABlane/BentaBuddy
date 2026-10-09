"""Single-owner local authentication. No email service or cloud identity provider."""
import hashlib
import hmac
import secrets
import threading
import time

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

COOKIE = 'bentabuddy_session'
SESSION_SECONDS = 24 * 60 * 60
ITERATIONS = 600000


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class SetupCredentials(Credentials):
    bakery_name: str = Field(min_length=1, max_length=100)


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), ITERATIONS).hex()


def install_auth(app, connect):
    attempts = {}
    attempt_lock = threading.Lock()

    def owner(db):
        return db.execute('SELECT * FROM auth_owner WHERE id=1').fetchone()

    def session_user(request):
        token = request.cookies.get(COOKIE)
        if not token:
            return None
        with connect() as db:
            row = db.execute('SELECT expires_at FROM auth_sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
            user = owner(db) if row and row['expires_at'] > time.time() else None
            return dict(email=user['email'], bakery_name=user['bakery_name']) if user else None

    def start_session(db, response, request):
        token = secrets.token_urlsafe(32)
        db.execute('DELETE FROM auth_sessions WHERE expires_at<=?', (int(time.time()),))
        db.execute('INSERT INTO auth_sessions VALUES (?,?)', (hashlib.sha256(token.encode()).hexdigest(), int(time.time()) + SESSION_SECONDS))
        response.set_cookie(COOKIE, token, httponly=True, samesite='strict', secure=request.url.scheme == 'https', max_age=SESSION_SECONDS, path='/')
        response.headers['Cache-Control'] = 'no-store'

    @app.middleware('http')
    async def authentication(request: Request, call_next):
        path = request.url.path
        if path.startswith('/api/') and path != '/api/facebook/webhook':
            public = path in ['/api/auth/status', '/api/auth/setup', '/api/auth/login']
            if request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
                # Cross-site forms cannot send JSON. Also reject cross-origin fetches.
                origin = request.headers.get('origin')
                expected_origin = str(request.base_url).rstrip('/')
                if (origin and origin != expected_origin) or request.headers.get('content-type', '').split(';')[0] != 'application/json':
                    return JSONResponse({'detail': 'Please submit from the BentaBuddy website.'}, status_code=403)
            if not public and not session_user(request):
                return JSONResponse({'detail': 'Please sign in to your bakery.'}, status_code=401, headers={'Cache-Control': 'no-store'})
        response = await call_next(request)
        if path.startswith('/api/'):
            response.headers['Cache-Control'] = 'no-store'
        return response

    @app.get('/api/auth/status')
    def status(request: Request):
        with connect() as db:
            needs_setup = owner(db) is None
        return {'needs_setup': needs_setup, 'user': session_user(request)}

    @app.post('/api/auth/setup')
    def setup(body: SetupCredentials, request: Request, response: Response):
        email = body.email.strip().lower()
        name = body.bakery_name.strip()
        if '@' not in email or not name or len(body.password) < 10:
            raise HTTPException(400, 'Enter your bakery name, a valid email, and a password of at least 10 characters.')
        with connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if owner(db):
                raise HTTPException(409, 'Your bakery account already exists. Please sign in.')
            salt = secrets.token_hex(16)
            db.execute('INSERT INTO auth_owner VALUES (1,?,?,?,?)', (email, name, salt, password_hash(body.password, salt)))
            start_session(db, response, request)
        return {'user': {'email': email, 'bakery_name': name}}

    @app.post('/api/auth/login')
    def login(body: Credentials, request: Request, response: Response):
        # Bound guessing on the local owner account without persisting client IPs.
        key = request.client.host if request.client else 'local'
        stamp = time.time()
        with attempt_lock:
            recent = [t for t in attempts.get(key, []) if t > stamp - 900]
            attempts[key] = recent
            if len(recent) >= 10:
                raise HTTPException(429, 'Too many attempts. Please try again in 15 minutes.')
            recent.append(stamp)
        with connect() as db:
            user = owner(db)
            salt = user['salt'] if user else '00' * 16
            candidate = password_hash(body.password, salt)
            if not user or not hmac.compare_digest(candidate, user['password_hash']) or body.email.strip().lower() != user['email']:
                raise HTTPException(401, 'The email or password is incorrect.')
            start_session(db, response, request)
            result = {'user': {'email': user['email'], 'bakery_name': user['bakery_name']}}
        with attempt_lock:
            attempts.pop(key, None)
        return result

    @app.post('/api/auth/logout')
    def logout(request: Request, response: Response):
        token = request.cookies.get(COOKIE, '')
        with connect() as db:
            db.execute('DELETE FROM auth_sessions WHERE token_hash=?', (hashlib.sha256(token.encode()).hexdigest(),))
        response.delete_cookie(COOKIE, path='/')
        return {'ok': True}
