"""Local encrypted snapshot packaging; never configures off-host storage/services."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import time

from nocturne.research.encrypted_backup import seal_snapshot, open_snapshot
from nocturne.research.recovery import verify_relocated_evidence

ROOT = Path(__file__).resolve().parents[1]


def known_secrets():
    values = []
    for name in ('DATABENTO_API_KEY', 'FRED_API_KEY', 'BLS_API_KEY', 'NASDAQ_DATA_LINK_API_KEY'):
        value = os.environ.get(name)
        if value:
            values.append(value.encode())
    for name in ('NOCTURNE_API_READER_TOKEN_FILE', 'NOCTURNE_API_ADMIN_TOKEN_FILE'):
        path = os.environ.get(name)
        if path:
            file = Path(path)
            if not file.is_file() or file.stat().st_size > 256:
                raise ValueError('invalid secret-exclusion configuration')
            values.append(file.read_bytes().strip())
    return values


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest='mode', required=True)
    generate = commands.add_parser('keygen')
    generate.add_argument('--key-file', type=Path, required=True)
    pack = commands.add_parser('pack')
    pack.add_argument('--snapshot', type=Path, required=True)
    pack.add_argument('--output', type=Path, required=True)
    pack.add_argument('--key-file', type=Path, required=True)
    pack.add_argument('--report', type=Path, required=True)
    restore = commands.add_parser('restore')
    restore.add_argument('--archive', type=Path, required=True)
    restore.add_argument('--destination', type=Path, required=True)
    restore.add_argument('--key-file', type=Path, required=True)
    restore.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.mode == 'keygen':
        path = args.key_file.resolve()
        if path.is_relative_to(ROOT):
            raise ValueError('backup key custody must be outside the repository')
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_BINARY', 0), 0o600)
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(secrets.token_bytes(32))
            handle.flush()
            os.fsync(handle.fileno())
        print(json.dumps({'status': 'PRIVATE_KEY_FILE_CREATED', 'key_material_logged': False,
                          'limits': 'Operator must protect Windows ACLs and arrange independent custody; no off-host transfer.'}))
        return
    started = time.monotonic()
    if args.mode == 'pack':
        result = seal_snapshot(args.snapshot, args.output, args.key_file, known_secrets())
    else:
        result = open_snapshot(args.archive, args.destination, args.key_file, known_secrets())
        result['evidence'] = verify_relocated_evidence(args.destination)
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'mode': args.mode,
              'elapsed_seconds': time.monotonic() - started, 'result': result,
              'off_host_status': 'OFF_HOST_VERIFICATION_REQUIRED', 'trading_decision': 'NO_TRADE'}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'mode': args.mode, 'status': result['status'], 'off_host_status': report['off_host_status']}))


if __name__ == '__main__':
    main()
