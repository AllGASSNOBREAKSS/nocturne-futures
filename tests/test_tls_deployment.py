"""Real loopback TLS handshake with an ephemeral test cert; no trust-store edits."""
from datetime import datetime, timedelta, timezone
import ipaddress
import os
import socket
import ssl
import threading
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import requests
import uvicorn

from nocturne.api import create_app, ForecastService
from test_api_security import READER, auth, secured


def test_real_tls_protects_authenticated_api_and_rejects_plaintext(tmp_path):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost isolated fixture')])
    now = datetime.now(timezone.utc)
    certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
                   .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
                   .not_valid_after(now + timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
                   .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False)
                   .sign(key, hashes.SHA256()))
    cert_file, key_file = tmp_path / 'tls-test.crt', tmp_path / 'tls-test.key'
    cert_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    if os.name != 'nt':
        key_file.chmod(0o600)
    _, _, policy = secured(tmp_path)
    logs = []
    app = create_app(ForecastService(tmp_path / 'j', tmp_path / 'm', tmp_path / 'f'), security=policy, audit=logs.append)
    bound = socket.socket()
    bound.bind(('127.0.0.1', 0))
    port = bound.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, ssl_certfile=str(cert_file), ssl_keyfile=str(key_file),
                                         ssl_version=ssl.PROTOCOL_TLS_SERVER, ssl_ciphers='ECDHE+AESGCM:ECDHE+CHACHA20',
                                         access_log=False, proxy_headers=False, timeout_graceful_shutdown=2, log_level='critical'))
    thread = threading.Thread(target=server.run, kwargs={'sockets': [bound]}, daemon=True)
    thread.start()
    try:
        deadline = time.monotonic() + 10
        while not server.started and thread.is_alive() and time.monotonic() < deadline:
            time.sleep(0.02)
        assert server.started
        session = requests.Session()
        session.trust_env = False
        url = f'https://127.0.0.1:{port}'
        response = session.get(url + '/v1/levels?instrument=NQ', headers=auth(), verify=str(cert_file), timeout=5)
        assert response.status_code == 200
        assert response.headers['strict-transport-security'].startswith('max-age=')
        assert session.get(url + '/v1/levels?instrument=NQ', verify=str(cert_file), timeout=5).status_code == 401
        context = ssl.create_default_context(cafile=str(cert_file))
        with socket.create_connection(('127.0.0.1', port), timeout=5) as raw:
            with context.wrap_socket(raw, server_hostname='127.0.0.1') as tls:
                assert tls.version() in ('TLSv1.2', 'TLSv1.3')
        try:
            plain = session.get(f'http://127.0.0.1:{port}/health', timeout=2)
        except requests.RequestException:
            plain = None
        assert plain is None or plain.status_code != 200
        assert READER not in str(logs)
        session.close()
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        bound.close()
    assert not thread.is_alive()
