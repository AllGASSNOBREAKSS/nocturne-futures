"""Single-process read-only API perimeter. No tokens, bodies or queries in logs."""
import asyncio
from collections import OrderedDict, deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import re
import time
import uuid

from starlette.responses import JSONResponse

from ..shadow.locking import FileLock

PUBLIC = {'/health', '/health/live'}
READER = {'/v1/predictions/latest', '/v1/levels', '/v1/auction/profile', '/v1/intermarket/state',
          '/v1/premarket/state', '/v1/forecast/v1', '/v1/forecast/bundle', '/v1/events/upcoming',
          '/v1/shadow/ndx-range', '/v1/shadow/history', '/v1/shadow/evaluation', '/v1/shadow/outcomes',
          '/v1/shadow/missed', '/v1/shadow/calibration', '/v1/alerts/critical-day', '/v1/market-state'}
ADMIN = {'/health/ready', '/v1/models/status', '/v1/research/status', '/v1/shadow/operations',
         '/v1/data/revisions', '/v1/data/reconciliations', '/v1/data/futures-readiness',
         '/v1/data/health', '/v1/shadow/verification'}
TOKEN = re.compile(r'[A-Za-z0-9_-]{32,128}')


def secret_digest(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 256:
        raise ValueError('invalid API secret configuration')
    if os.name != 'nt' and path.stat().st_mode & 0o077:
        raise ValueError('API secret file must be owner-only')
    value = path.read_bytes().strip()
    if not TOKEN.fullmatch(value.decode('ascii', errors='replace')):
        raise ValueError('invalid API secret configuration')
    return hashlib.sha256(value).digest()


class AuditLog:
    def __init__(self, path, max_bytes=8 * 1024**2):
        self.path = Path(path)
        self.max_bytes = max_bytes

    def __call__(self, record):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(self.path.with_suffix('.lock')):
            encoded = (json.dumps(record, sort_keys=True) + '\n').encode()
            if (self.path.stat().st_size if self.path.exists() else 0) + len(encoded) > self.max_bytes:
                raise OSError('audit retention capacity reached; operator rotation required')
            with self.path.open('ab') as handle:
                handle.write(encoded)
                handle.flush()
                os.fsync(handle.fileno())


@dataclass(frozen=True)
class SecurityPolicy:
    reader_digest: bytes | None = field(default=None, repr=False)
    admin_digest: bytes | None = field(default=None, repr=False)
    internal_loopback: bool = False
    allowed_hosts: tuple = ('127.0.0.1', 'localhost', '[::1]')
    max_body: int = 65536
    max_headers: int = 16384
    peer_per_minute: int = 120
    principal_per_minute: int = 60
    max_peers: int = 1024

    def __post_init__(self):
        if self.reader_digest and self.reader_digest == self.admin_digest:
            raise ValueError('reader and administrator credentials must differ')
        if any(not 1 <= n <= limit for n, limit in ((self.max_body, 1048576), (self.max_headers, 65536),
               (self.peer_per_minute, 1000), (self.principal_per_minute, 1000), (self.max_peers, 4096))):
            raise ValueError('invalid API resource bounds')
        if not self.allowed_hosts or any('*' in h or '/' in h or '@' in h for h in self.allowed_hosts):
            raise ValueError('explicit API host allowlist required')

    @classmethod
    def from_env(cls):
        reader = os.environ.get('NOCTURNE_API_READER_TOKEN_FILE')
        admin = os.environ.get('NOCTURNE_API_ADMIN_TOKEN_FILE')
        hosts = tuple(h.strip().lower() for h in os.environ.get('NOCTURNE_API_ALLOWED_HOSTS', '127.0.0.1,localhost,[::1]').split(',') if h.strip())
        return cls(reader_digest=secret_digest(reader) if reader else None,
                   admin_digest=secret_digest(admin) if admin else None, allowed_hosts=hosts)

    @classmethod
    def internal(cls):
        # Explicit embedded/test compatibility only. CLI/environment never enables
        # this bypass; real peers must still be loopback (testclient is synthetic).
        return cls(internal_loopback=True, allowed_hosts=('testserver', 'localhost', '127.0.0.1', '[::1]'))


class WindowLimiter:
    def __init__(self, capacity, clock=time.monotonic):
        self.capacity, self.clock = capacity, clock
        self.windows = OrderedDict()

    def allow(self, key, limit):
        now = self.clock()
        for old in list(self.windows):
            if not self.windows[old] or self.windows[old][-1] <= now - 60:
                del self.windows[old]
        if key not in self.windows:
            if len(self.windows) >= self.capacity:
                return False
            self.windows[key] = deque()
        queue = self.windows[key]
        while queue and queue[0] <= now - 60:
            queue.popleft()
        if len(queue) >= limit:
            return False
        queue.append(now)
        return True


class SecurityMiddleware:
    def __init__(self, app, policy, audit, clock=time.monotonic):
        self.app, self.policy, self.audit = app, policy, audit
        self.peers = WindowLimiter(policy.max_peers, clock)
        self.principals = WindowLimiter(2, clock)

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            if scope['type'] == 'websocket':
                await send({'type': 'websocket.close', 'code': 1008})
            else:
                await self.app(scope, receive, send)
            return
        path, method = scope.get('path', ''), scope['method']
        label = path if path in PUBLIC | READER | ADMIN else 'UNMATCHED'
        prediction = bool(re.fullmatch(r'/v1/predictions/[A-Za-z0-9_-]{1,128}', path))
        if prediction and path != '/v1/predictions/latest':
            label = '/v1/predictions/{prediction_id}'
        request_id, role = uuid.uuid4().hex, 'anonymous'
        started = False

        async def guarded_send(message):
            nonlocal started
            if message['type'] == 'http.response.start':
                record = {'at': datetime.now(timezone.utc).isoformat(), 'request_id': request_id,
                          'route': label, 'method': method if method in ('GET', 'HEAD', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS') else 'OTHER',
                          'status': message['status'], 'role': role}
                try:
                    self.audit(record)
                except Exception:
                    raise OSError('API audit unavailable') from None
                headers = list(message.get('headers', []))
                headers += [(b'cache-control', b'no-store'), (b'x-content-type-options', b'nosniff'),
                            (b'referrer-policy', b'no-referrer'), (b'content-security-policy', b"default-src 'none'"),
                            (b'x-request-id', request_id.encode())]
                if scope.get('scheme') == 'https':
                    headers.append((b'strict-transport-security', b'max-age=31536000'))
                message = {**message, 'headers': headers}
                started = True
            await send(message)

        async def reject(status, detail, headers=None):
            await JSONResponse({'detail': detail}, status_code=status, headers=headers)(scope, receive, guarded_send)

        try:
            headers = scope.get('headers', [])
            if len(headers) > 100 or sum(len(k) + len(v) for k, v in headers) > self.policy.max_headers:
                return await reject(431, 'request headers too large')
            if len(scope.get('raw_path', path.encode())) > 2048 or len(scope.get('query_string', b'')) > 4096:
                return await reject(414, 'request target too large')
            hosts = [v.decode('ascii', errors='replace').lower() for k, v in headers if k == b'host']
            host = hosts[0] if len(hosts) == 1 else ''
            host = host.split(']')[0] + ']' if host.startswith('[') and ']' in host else host.split(':')[0]
            if host not in self.policy.allowed_hosts:
                return await reject(400, 'host not allowed')
            peer = (scope.get('client') or ('unknown', 0))[0]
            if not self.peers.allow(peer, self.policy.peer_per_minute):
                return await reject(429, 'request rate exceeded', {'Retry-After': '60'})
            lengths = [v for k, v in headers if k == b'content-length']
            if len(lengths) > 1 or (lengths and (len(lengths[0]) > 10 or not lengths[0].isdigit() or any(k == b'transfer-encoding' for k, v in headers))):
                return await reject(400, 'ambiguous request length')
            if lengths and int(lengths[0]) > self.policy.max_body:
                return await reject(413, 'request body too large')
            if self.policy.internal_loopback:
                try:
                    local = ipaddress.ip_address(peer).is_loopback
                except ValueError:
                    local = peer == 'testclient'
                if not local:
                    return await reject(403, 'internal API is loopback-only')
                role = 'admin'
            elif path not in PUBLIC:
                if not (self.policy.reader_digest or self.policy.admin_digest):
                    return await reject(503, 'API credentials not configured')
                auth = [v for k, v in headers if k == b'authorization']
                candidate = b''
                if len(auth) == 1 and auth[0].startswith(b'Bearer ') and len(auth[0]) <= 135:
                    candidate = hashlib.sha256(auth[0][7:]).digest()
                reader = hmac.compare_digest(candidate, self.policy.reader_digest or b'\0' * 32)
                admin = hmac.compare_digest(candidate, self.policy.admin_digest or b'\0' * 32)
                if not reader and not admin:
                    return await reject(401, 'authentication required', {'WWW-Authenticate': 'Bearer'})
                role = 'admin' if admin else 'reader'
                if not self.principals.allow(role, self.policy.principal_per_minute):
                    return await reject(429, 'credential rate exceeded', {'Retry-After': '60'})
                if role != 'admin' and path not in READER and not prediction:
                    return await reject(403, 'administrator role required')
            if method not in ('GET', 'HEAD'):
                return await reject(405, 'read-only API', {'Allow': 'GET, HEAD'})
            body = bytearray()
            try:
                async with asyncio.timeout(5):
                    for _ in range(1024):
                        message = await receive()
                        if message['type'] == 'http.disconnect':
                            return
                        body.extend(message.get('body', b''))
                        if len(body) > self.policy.max_body:
                            return await reject(413, 'request body too large')
                        if not message.get('more_body', False):
                            break
                    else:
                        return await reject(413, 'too many body fragments')
            except TimeoutError:
                return await reject(408, 'request body timeout')
            if lengths and len(body) != int(lengths[0]):
                return await reject(400, 'request length mismatch')
            consumed = False

            async def replay():
                nonlocal consumed
                if not consumed:
                    consumed = True
                    return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
                return await receive()

            await self.app(scope, replay, guarded_send)
        except Exception:
            if not started:
                # No response data can leave without a committed audit event.
                # If the sink itself is down, return only a generic unavailable.
                try:
                    await reject(503, 'API unavailable')
                except Exception:
                    await JSONResponse({'detail': 'API unavailable'}, status_code=503,
                                       headers={'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff'})(scope, receive, send)
            else:
                raise
