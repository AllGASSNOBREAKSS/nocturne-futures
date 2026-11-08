"""Bounded incident investigation; no forecast/outcome/reconciliation mutation."""
from datetime import datetime, timezone
import argparse
import json
from pathlib import Path

from nocturne.adapters.snapshots import SnapshotStore, canonical, digest, immutable_write
from nocturne.shadow import ShadowStore
from nocturne.shadow.reconciliation import incident_disposition
from phase3k_reconcile import import_existing, reference_check

ROOT = Path(__file__).resolve().parents[1]
IDS = ('291aac9c9d893a888609aafd', 'cd26071237a957cd7a874933')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reference-check', action='store_true', help='bounded public reference requests, never paid data')
    args = parser.parse_args()
    store = ShadowStore(ROOT / 'data/shadow/ndx_range')
    paths = (store.forecast_path, store.outcome_path, store.reconciliation_path)
    before = {p: p.read_bytes() if p.exists() else b'' for p in paths}
    archive = SnapshotStore(ROOT / 'data/shadow/market/snapshots')
    revised = import_existing(ROOT / 'data/shadow/market', '^NDX', archive)
    forecasts = {f['forecast_id']: f for f in store.forecasts()}
    now = datetime.now(timezone.utc)
    checks = {}
    if args.reference_check:
        sessions = sorted({forecasts[i][k] for i in IDS for k in ('data_date', 'target_date')
                           if forecasts[i][k] < now.date().isoformat()})
        for session in sessions:
            checks[session] = reference_check(archive.root, session=session)
    records = []
    for identifier in IDS:
        forecast = forecasts[identifier]
        evidence = [item for session in (forecast['data_date'], forecast['target_date']) for item in checks.get(session, [])]
        report = incident_disposition(forecast, archive, revised, now, evidence)
        encoded = canonical(report)
        immutable_write(archive.root / 'incident-dispositions' / f'{digest(encoded)}.json', encoded)
        (ROOT / 'reports' / f'phase3t_incident_{forecast["target_date"]}.json').write_text(json.dumps(report, indent=2) + '\n')
        records.append({k: report[k] for k in ('forecast_id', 'target_date', 'classification', 'verdict', 'eligible_for_evaluation', 'blocking_reasons')})
    if any((p.read_bytes() if p.exists() else b'') != data for p, data in before.items()):
        raise ValueError('journals changed during investigation; review concurrent writers before accepting report')
    summary = {'generated_at': now.isoformat(), 'records': records, 'journal_bytes_unchanged': True,
               'provider_requests': 'bounded public references only' if args.reference_check else 'none',
               'paid_consumption': False, 'trading_decision': 'NO_TRADE'}
    (ROOT / 'reports/phase3t_incidents.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary))


if __name__ == '__main__':
    main()
