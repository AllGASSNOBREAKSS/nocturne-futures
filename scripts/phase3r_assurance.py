"""Inventory genuine persisted work without enqueueing exhausted experiments."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path

from nocturne.research.orchestrator import JOB_TYPES
from nocturne.research.recovery import db_rows

ROOT = Path(__file__).resolve().parents[1]
PHASE_START = datetime(2026, 11, 6, 1, 30, tzinfo=timezone.utc)


def main():
    jobs = db_rows(ROOT / 'data/research/orchestrator/jobs.sqlite')['jobs']
    kinds = []
    for kind in JOB_TYPES:
        matching = [job for job in jobs if job['kind'] == kind]
        recent = [job for job in matching if job['updated'] >= PHASE_START.timestamp()]
        latest = max(matching, key=lambda j: j['updated']) if matching else None
        summary = None
        if latest:
            result = json.loads(latest['result']) if latest['result'] else {}
            summary = {'id': latest['id'], 'state': latest['state'], 'lane': latest['lane'],
                       'updated_at': datetime.fromtimestamp(latest['updated'], timezone.utc).isoformat(),
                       'payload': json.loads(latest['payload']), 'result_status': result.get('status'),
                       'scope': result.get('report', {}).get('scope', result.get('scope'))}
        kinds.append({'kind': kind, 'persisted_counts': dict(Counter(j['state'] for j in matching)),
                      'updated_in_phase_counts': dict(Counter(j['state'] for j in recent)), 'latest': summary,
                      'interpretation': 'Persisted engineering/job evidence; prior development diagnostics are not new independent validation.'})
    forward = json.loads((ROOT / 'reports/phase3i_forward.json').read_text())
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'phase_start_observed_at': PHASE_START.isoformat(),
              'job_types': kinds, 'forward': {k: forward[k] for k in ('issued', 'verified_matured', 'pending', 'inference_samples')},
              'new_market_training_eligible': False, 'reason': 'No new licensed data or independent hypothesis qualified; defaults do not repeat index experiments.',
              'futures': 'USER_ACTION_REQUIRED', 'promotion': 'NO_PROMOTION', 'trading_decision': 'NO_TRADE',
              'limits': 'States updated after phase start are observations, not a claim that every job type ran anew or that any model has predictive value.'}
    (ROOT / 'reports/phase3r_assurance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'types_in_inventory': len(kinds), 'updated_since_phase_start': {k['kind']: k['updated_in_phase_counts'] for k in kinds}, 'forward': report['forward']}))


if __name__ == '__main__':
    main()
