"""Authenticated packaging of an existing verified snapshot, never live capture.

AES-256-GCM with fresh nonces; key custody/off-host transfer are operator duties.
No unauthenticated plaintext is extracted or made into a restored snapshot.
"""
import base64
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import secrets
import struct
import tarfile
import tempfile

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from ..adapters.snapshots import canonical, digest
from .recovery import verify_files, safe_path, restore_snapshot, allowed

MAGIC = b'NCTBKP1\n'
CHUNK = 65536


def load_key(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size != 32:
        raise ValueError('backup key must be a separate 32-byte private file')
    if os.name != 'nt' and path.stat().st_mode & 0o077:
        raise ValueError('backup key file must be owner-only')
    return path.read_bytes()


def scan_secrets(root, known_secrets=(), max_bytes=1024**3):
    """Bounded exclusion check, not exhaustive DLP for unknown/encoded secrets."""
    root = Path(root).resolve()
    manifest = verify_files(root)
    needles = [bytes(v) for v in known_secrets if len(v) >= 8]
    needles += [b'-----BEGIN PRIVATE KEY-----', b'-----BEGIN RSA PRIVATE KEY-----', b'-----BEGIN EC PRIVATE KEY-----']
    overlap = max(map(len, needles)) - 1
    total = 0
    names = [e['path'] for e in manifest['files']] + ['manifest.json', 'manifest.sha256']
    for name in names:
        part = Path(name)
        if any(p.lower().startswith('.env') or 'credentials' in p.lower() for p in part.parts) or part.suffix.lower() in ('.key', '.pem', '.pfx', '.p12', '.secret'):
            raise ValueError('secret-exclusion check blocked packaging')
        path = safe_path(root, name)
        carry = b''
        with path.open('rb') as handle:
            while chunk := handle.read(CHUNK):
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError('secret scan byte budget exceeded')
                value = carry + chunk
                if any(needle in value for needle in needles):
                    raise ValueError('secret-exclusion check blocked packaging')
                carry = value[-overlap:] if overlap else b''
    return {'status': 'KNOWN_SECRET_AND_PATH_EXCLUSIONS_PASSED', 'files': len(names), 'bytes': total,
            'limits': 'Allowlisted snapshot scope, forbidden secret-file paths, private-key markers and supplied known values; unknown or encoded secrets require operator review.'}


def seal_snapshot(snapshot, output, key_file, known_secrets=(), max_bytes=1024**3):
    key = load_key(key_file)
    snapshot, output, key_file = Path(snapshot).resolve(), Path(output).resolve(), Path(key_file).resolve()
    if output.exists() or output.is_relative_to(snapshot) or key_file.is_relative_to(snapshot) or output == key_file:
        raise ValueError('new ciphertext output and separate key outside snapshot required')
    exclusion = scan_secrets(snapshot, (*known_secrets, key), max_bytes)
    manifest = verify_files(snapshot)
    header = {'schema': 1, 'cipher': 'AES-256-GCM', 'nonce': base64.b64encode(secrets.token_bytes(12)).decode(),
              'manifest_sha256': digest((snapshot / 'manifest.json').read_bytes()),
              'created_at': datetime.now(timezone.utc).isoformat()}
    encoded = canonical(header)
    aad = MAGIC + struct.pack('>I', len(encoded)) + encoded
    encryptor = Cipher(algorithms.AES(key), modes.GCM(base64.b64decode(header['nonce']))).encryptor()
    encryptor.authenticate_additional_data(aad)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as target:
        target.write(aad)
        class Writer:
            total = 0
            def write(self, data):
                self.total += len(data)
                if self.total > max_bytes:
                    raise ValueError('encrypted package byte budget exceeded')
                target.write(encryptor.update(data))
                return len(data)
        writer = Writer()
        with tarfile.open(fileobj=writer, mode='w|', format=tarfile.USTAR_FORMAT) as archive:
            for name in ['manifest.json', 'manifest.sha256'] + [e['path'] for e in manifest['files']]:
                source = safe_path(snapshot, name)
                info = tarfile.TarInfo(name)
                info.size, info.mode = source.stat().st_size, 0o600
                with source.open('rb') as content:
                    archive.addfile(info, content)
        verify_files(snapshot)
        target.write(encryptor.finalize())
        target.write(encryptor.tag)
        target.flush()
        os.fsync(target.fileno())
    return {'status': 'ENCRYPTED_VERIFIED_SNAPSHOT', 'schema': 1, 'cipher': header['cipher'],
            'manifest_sha256': header['manifest_sha256'], 'ciphertext_bytes': output.stat().st_size,
            'secret_exclusion': exclusion,
            'limits': 'Local packaging only; not off-host durability, authorized key custody or protection against an operator changing both archive and key.'}


def open_snapshot(archive_path, destination, key_file, known_secrets=(), max_bytes=1024**3):
    archive_path, destination = Path(archive_path).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError('restore destination must be new')
    key = load_key(key_file)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='nocturne-decrypt-', dir=destination.parent) as private:
        staging = Path(private)
        plaintext = staging / 'authenticated.tar'
        with archive_path.open('rb') as source:
            if source.read(len(MAGIC)) != MAGIC:
                raise ValueError('unsupported encrypted backup format')
            length_bytes = source.read(4)
            if len(length_bytes) != 4:
                raise ValueError('truncated backup header')
            length = struct.unpack('>I', length_bytes)[0]
            if not 1 <= length <= 8192:
                raise ValueError('backup header budget exceeded')
            encoded = source.read(length)
            header = json.loads(encoded)
            if header.get('schema') != 1 or header.get('cipher') != 'AES-256-GCM':
                raise ValueError('unsupported encrypted backup cipher/schema')
            nonce = base64.b64decode(header['nonce'], validate=True)
            if len(nonce) != 12:
                raise ValueError('invalid backup nonce')
            offset = source.tell()
            remaining = archive_path.stat().st_size - offset - 16
            if not 1 <= remaining <= max_bytes:
                raise ValueError('encrypted backup size invalid')
            source.seek(-16, 2)
            tag = source.read(16)
            source.seek(offset)
            decryptor = Cipher(algorithms.AES(key), modes.GCM(nonce, tag)).decryptor()
            decryptor.authenticate_additional_data(MAGIC + length_bytes + encoded)
            with plaintext.open('xb') as target:
                if os.name != 'nt':
                    plaintext.chmod(0o600)
                while remaining:
                    chunk = source.read(min(CHUNK, remaining))
                    if not chunk:
                        raise ValueError('truncated ciphertext')
                    target.write(decryptor.update(chunk))
                    remaining -= len(chunk)
                target.write(decryptor.finalize())  # Authentication before extraction.
        extracted = staging / 'snapshot'
        extracted.mkdir()
        names, total = set(), 0
        with tarfile.open(plaintext, mode='r|') as archive:
            for member in archive:
                name = member.name
                if not member.isfile() or name in names or len(names) >= 20000 or member.size < 0:
                    raise ValueError('unsafe or duplicate backup member')
                if name not in ('manifest.json', 'manifest.sha256') and not allowed(name):
                    raise ValueError('unexpected backup member scope')
                path = safe_path(extracted, name)
                if path.relative_to(extracted).as_posix() != name:
                    raise ValueError('noncanonical backup member')
                total += member.size
                if total > max_bytes:
                    raise ValueError('restored byte budget exceeded')
                names.add(name)
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as incoming, path.open('xb') as target:
                    while chunk := incoming.read(CHUNK):
                        target.write(chunk)
        verify_files(extracted)
        if digest((extracted / 'manifest.json').read_bytes()) != header['manifest_sha256']:
            raise ValueError('encrypted manifest binding mismatch')
        exclusion = scan_secrets(extracted, (*known_secrets, key), max_bytes)
        result = restore_snapshot(extracted, destination)
    return {**result, 'authentication': 'AES_GCM_TAG_VERIFIED_BEFORE_EXTRACTION', 'secret_exclusion': exclusion,
            'off_host_status': 'OFF_HOST_VERIFICATION_REQUIRED'}
