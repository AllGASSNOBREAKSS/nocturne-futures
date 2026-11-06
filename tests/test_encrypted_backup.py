import io
import json
import os
from pathlib import Path
import struct
import tarfile

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from nocturne.adapters.snapshots import canonical
from nocturne.research.encrypted_backup import seal_snapshot, open_snapshot, scan_secrets, MAGIC, CHUNK
from nocturne.research.recovery import snapshot_evidence, verify_files
from test_recovery_snapshot import project_fixture, SAFE_TIME


def setup_snapshot(tmp_path, extra=None):
    root = project_fixture(tmp_path)
    if extra:
        path = root / 'data/research/orchestrator' / extra[0]
        path.write_bytes(extra[1])
    snapshot = tmp_path / 'snapshot'
    snapshot_evidence(root, snapshot, now=SAFE_TIME)
    key = tmp_path / 'private-backup.key'
    key.write_bytes(os.urandom(32))
    if os.name != 'nt':
        key.chmod(0o600)
    return snapshot, key


def test_authenticated_roundtrip_preserves_all_bytes_without_activating_services(tmp_path):
    snapshot, key = setup_snapshot(tmp_path)
    before = (snapshot / 'data/shadow/ndx_range/forecasts.jsonl').read_bytes()
    sealed = tmp_path / 'backup.nct'
    report = seal_snapshot(snapshot, sealed, key)
    restored = tmp_path / 'restored'
    result = open_snapshot(sealed, restored, key)
    assert result['authentication'] == 'AES_GCM_TAG_VERIFIED_BEFORE_EXTRACTION'
    assert result['off_host_status'] == 'OFF_HOST_VERIFICATION_REQUIRED'
    assert report['secret_exclusion']['status'].endswith('PASSED')
    verify_files(restored)
    assert (restored / 'data/shadow/ndx_range/forecasts.jsonl').read_bytes() == before
    assert (snapshot / 'data/shadow/ndx_range/forecasts.jsonl').read_bytes() == before
    assert b'forecasts.jsonl' not in sealed.read_bytes()
    assert not list(tmp_path.glob('nocturne-decrypt-*'))


@pytest.mark.parametrize('failure', ['wrong-key', 'ciphertext', 'truncation'])
def test_wrong_key_or_corruption_never_extracts_unauthenticated_plaintext(tmp_path, failure):
    snapshot, key = setup_snapshot(tmp_path)
    sealed = tmp_path / 'backup.nct'
    seal_snapshot(snapshot, sealed, key)
    if failure == 'wrong-key':
        key.write_bytes(os.urandom(32))
    else:
        data = bytearray(sealed.read_bytes())
        if failure == 'ciphertext':
            data[-32] ^= 1
        else:
            del data[-5:]
        sealed.write_bytes(data)
    with pytest.raises((ValueError, InvalidTag)):
        open_snapshot(sealed, tmp_path / 'restored', key)
    assert not (tmp_path / 'restored').exists()
    assert not list(tmp_path.glob('nocturne-decrypt-*'))


@pytest.mark.parametrize('kind', ['path', 'known-secret', 'private-key'])
def test_secret_exclusion_is_enforced_before_any_ciphertext_output(tmp_path, kind):
    name, content, known = 'notes.txt', b'ordinary fixture', []
    if kind == 'path':
        name = 'credentials.json'
    elif kind == 'known-secret':
        secret = b'fixture-known-sensitive-value'
        content = b'x' * (CHUNK - 4) + secret + b'after'
        known = [secret]
    else:
        content = b'-----BEGIN PRIVATE KEY-----\nfixture only'
    snapshot, key = setup_snapshot(tmp_path, (name, content))
    with pytest.raises(ValueError, match='secret-exclusion'):
        seal_snapshot(snapshot, tmp_path / 'blocked.nct', key, known)
    assert not (tmp_path / 'blocked.nct').exists()


def test_existing_outputs_and_tiny_budgets_cannot_overwrite_user_files(tmp_path):
    snapshot, key = setup_snapshot(tmp_path)
    output = tmp_path / 'existing.nct'
    output.write_bytes(b'preserve')
    with pytest.raises(ValueError):
        seal_snapshot(snapshot, output, key)
    assert output.read_bytes() == b'preserve'
    with pytest.raises(ValueError, match='budget'):
        scan_secrets(snapshot, max_bytes=1)


@pytest.mark.parametrize('member_name,link', [('../escape', False), ('data/research/orchestrator/link', True)])
def test_even_authenticated_unsafe_tar_members_cannot_escape_staging(tmp_path, member_name, link):
    key = tmp_path / 'fixture.key'
    key.write_bytes(os.urandom(32))
    if os.name != 'nt':
        key.chmod(0o600)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w') as tar:
        member = tarfile.TarInfo(member_name)
        if link:
            member.type, member.linkname = tarfile.SYMTYPE, '../../escape'
            tar.addfile(member)
        else:
            member.size = 3
            tar.addfile(member, io.BytesIO(b'bad'))
    nonce = os.urandom(12)
    import base64
    header = canonical({'schema': 1, 'cipher': 'AES-256-GCM', 'nonce': base64.b64encode(nonce).decode(), 'manifest_sha256': '0' * 64})
    aad = MAGIC + struct.pack('>I', len(header)) + header
    sealed = tmp_path / 'malicious-fixture.nct'
    sealed.write_bytes(aad + AESGCM(key.read_bytes()).encrypt(nonce, buffer.getvalue(), aad))
    with pytest.raises(ValueError):
        open_snapshot(sealed, tmp_path / 'restored', key)
    assert not (tmp_path / 'escape').exists()
    assert not (tmp_path / 'restored').exists()
