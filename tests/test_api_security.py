from dataclasses import replace
import hashlib
import json
import os

from fastapi.testclient import TestClient
import pytest

from nocturne.api import create_app, ForecastService
from nocturne.api.security import SecurityPolicy, WindowLimiter, AuditLog, secret_digest

READER = 'fixture_reader_' + 'r' * 32
ADMIN = 'fixture_admin_' + 'a' * 32


def secured(tmp_path, **options):
    records = []
    policy = SecurityPolicy(reader_digest=hashlib.sha256(READER.encode()).digest(),
                            admin_digest=hashlib.sha256(ADMIN.encode()).digest(),
                            allowed_hosts=('testserver', 'localhost', '127.0.0.1'))
    policy = replace(policy, **options)
    service = ForecastService(tmp_path / 'journal', tmp_path / 'models', tmp_path / 'forecasts')
    return TestClient(create_app(service, security=policy, audit=records.append)), records, policy


def auth(token=READER):
    return {'Authorization': 'Bearer ' + token}


def test_authentication_role_separation_and_minimal_liveness(tmp_path):
    client, records, _ = secured(tmp_path)
    assert client.get('/health').json() == {'status': 'alive', 'read_only': True}
    assert client.get('/health/live').status_code == 200
    assert client.get('/health/ready').status_code == 401
    assert client.get('/v1/levels?instrument=NQ').status_code == 401
    assert client.get('/v1/levels?instrument=NQ', headers=auth('invalid')).status_code == 401
    assert client.get('/v1/levels?instrument=NQ', headers=auth()).status_code == 200
    for route in ('/v1/research/status', '/v1/models/status', '/v1/shadow/operations', '/v1/data/revisions', '/health/ready'):
        assert client.get(route, headers=auth()).status_code == 403
        assert client.get(route, headers=auth(ADMIN)).status_code == 200
    assert client.post('/v1/research/status', headers=auth(ADMIN)).status_code == 405
    assert client.get('/openapi.json').status_code == 401
    assert client.get('/openapi.json', headers=auth(ADMIN)).status_code == 404
    assert all(READER not in json.dumps(r) and ADMIN not in json.dumps(r) for r in records)


def test_no_credentials_fail_closed_without_breaking_liveness(tmp_path):
    service = ForecastService(tmp_path / 'journal', tmp_path / 'models', tmp_path / 'forecasts')
    client = TestClient(create_app(service, security=SecurityPolicy(allowed_hosts=('testserver',)), audit=lambda r: None))
    assert client.get('/health/live').status_code == 200
    assert client.get('/v1/levels?instrument=NQ').status_code == 503


def test_rate_limits_do_not_trust_forwarded_headers_and_storage_is_bounded(tmp_path):
    client, records, _ = secured(tmp_path, peer_per_minute=2)
    assert client.get('/health').status_code == 200
    assert client.get('/health', headers={'X-Forwarded-For': '192.0.2.1'}).status_code == 200
    response = client.get('/health', headers={'X-Forwarded-For': '192.0.2.2'})
    assert response.status_code == 429 and response.headers['retry-after'] == '60'
    clock = [0]
    limiter = WindowLimiter(1, lambda: clock[0])
    assert limiter.allow('a', 1)
    assert not limiter.allow('b', 1)
    clock[0] = 61
    assert limiter.allow('b', 1)
    assert len(limiter.windows) == 1


def test_credential_rate_limit_is_separate_from_peer_limit(tmp_path):
    client, _, _ = secured(tmp_path, principal_per_minute=1)
    assert client.get('/v1/levels?instrument=NQ', headers=auth()).status_code == 200
    assert client.get('/v1/levels?instrument=NQ', headers=auth()).status_code == 429
    assert client.get('/v1/models/status', headers=auth(ADMIN)).status_code == 200


def test_request_bounds_host_and_security_headers(tmp_path):
    client, _, _ = secured(tmp_path, max_body=16, max_headers=1024)
    assert client.request('GET', '/health', content=b'x' * 17).status_code == 413
    assert client.get('/health', headers={'X-Large': 'x' * 2000}).status_code == 431
    assert client.get('/health', headers={'Host': 'attacker.invalid'}).status_code == 400
    assert client.get('/health?' + 'x' * 4097).status_code == 414
    assert client.request('GET', '/health', headers=[('Content-Length', '0'), ('Content-Length', '1')]).status_code == 400
    response = client.get('/health')
    assert response.headers['cache-control'] == 'no-store'
    assert response.headers['x-content-type-options'] == 'nosniff'
    assert len(response.headers['x-request-id']) == 32


def test_chunked_body_and_audit_capacity_fail_closed(tmp_path):
    client, _, _ = secured(tmp_path, max_body=16)
    assert client.request('GET', '/health', content=iter([b'x' * 10, b'x' * 10])).status_code == 413
    with pytest.raises(OSError, match='capacity'):
        AuditLog(tmp_path / 'audit.jsonl', max_bytes=1)({'status': 200})


def test_audit_never_records_queries_unknown_paths_headers_or_tokens(tmp_path):
    client, records, _ = secured(tmp_path)
    client.get('/v1/levels', params={'instrument': 'NQ', 'secret': READER}, headers=auth())
    client.get('/' + ADMIN, headers=auth(ADMIN))
    text = json.dumps(records)
    assert READER not in text and ADMIN not in text and 'authorization' not in text.lower()
    assert any(r['route'] == 'UNMATCHED' for r in records)
    path = tmp_path / 'audit/log.jsonl'
    AuditLog(path)(records[0])
    assert json.loads(path.read_text())['status'] == 200


def test_audit_failure_never_releases_protected_data(tmp_path):
    _, _, policy = secured(tmp_path)
    service = ForecastService(tmp_path / 'journal', tmp_path / 'models', tmp_path / 'forecasts')
    def broken(record):
        raise OSError('fixture only')
    client = TestClient(create_app(service, security=policy, audit=broken))
    assert client.get('/v1/levels?instrument=NQ', headers=auth()).status_code == 503


def test_secret_configuration_is_file_only_and_repr_safe(tmp_path, monkeypatch):
    path = tmp_path / 'reader.secret'
    path.write_text(READER)
    if os.name != 'nt':
        path.chmod(0o600)
    monkeypatch.setenv('NOCTURNE_API_READER_TOKEN_FILE', str(path))
    monkeypatch.delenv('NOCTURNE_API_ADMIN_TOKEN_FILE', raising=False)
    policy = SecurityPolicy.from_env()
    assert policy.reader_digest == secret_digest(path)
    assert READER not in repr(policy)
    with pytest.raises(ValueError, match='differ'):
        replace(policy, admin_digest=policy.reader_digest)
    path.write_text('too-short')
    with pytest.raises(ValueError):
        SecurityPolicy.from_env()


def test_internal_compatibility_cannot_be_used_remotely(tmp_path):
    service = ForecastService(tmp_path / 'journal', tmp_path / 'models', tmp_path / 'forecasts')
    client = TestClient(create_app(service, security=SecurityPolicy.internal(), audit=lambda r: None), client=('192.0.2.1', 1234))
    assert client.get('/v1/levels?instrument=NQ').status_code == 403


def test_cli_refuses_unapproved_remote_binding(monkeypatch, tmp_path):
    from nocturne.cli import _serve
    path = tmp_path / 'reader.secret'
    path.write_text(READER)
    if os.name != 'nt':
        path.chmod(0o600)
    monkeypatch.setenv('NOCTURNE_API_READER_TOKEN_FILE', str(path))
    monkeypatch.delenv('NOCTURNE_API_ADMIN_TOKEN_FILE', raising=False)
    with pytest.raises(ValueError, match='non-loopback'):
        _serve('0.0.0.0', 8000)
