"""Timestamped evidence and blockers; successful collection is not deployment GO."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = 'c65e5960864be85b760d5953725d72ea5bca6ce4'


def read(name):
    return json.loads((ROOT / 'reports' / name).read_text(encoding='utf-8-sig'))


def main():
    preservation = []
    for name in ('data/shadow/ndx_range/forecasts.jsonl', 'data/shadow/ndx_range/outcomes.jsonl',
                 'models/shadow/ndx-range-v1/model.joblib'):
        original = subprocess.check_output(['git', 'show', f'{BASE}:{name}'], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        intact = current.startswith(original) if name.endswith('.jsonl') else current == original
        preservation.append({'path': name, 'original_bytes_preserved': intact,
                             'appended_bytes': len(current) - len(original) if intact else None,
                             'sha256': hashlib.sha256(current).hexdigest()})
    forward = read('phase3i_forward.json')
    report = {'generated_at': datetime.now(timezone.utc).isoformat(), 'baseline_commit': BASE,
              'decision': 'NO_GO_FRONTEND', 'preservation': preservation,
              'engineering': {'dependency_lock': read('phase3r_dependency_lock.json'),
                              'runtime': read('phase3r_runtime.json'),
                              'recovery': read('phase3r_recovery_check.json'),
                              'scheduler': read('phase3r_scheduler.json'),
                              'assurance': 'reports/phase3r_assurance.json'},
              'forward': {k: forward[k] for k in ('generated_at', 'issued', 'verified_matured', 'pending', 'inference_samples', 'outcome_verification')},
              'futures_access': read('phase3r_data_access.json'),
              'engineering_open_gates': ['Separate-host/OS restore and authorized encrypted off-host backup with independent key custody',
                                         'Unattended account/always-on deployment, reboot/logoff/long-soak evidence and independent monitoring',
                                         'API authentication/TLS/rate-limit/load/security review before any non-loopback deployment',
                                         'Hard process-memory isolation and reviewed live-path cutover/rollback'],
              'quantitative_open_gates': ['Authorized genuine NQ/ES receipts, sufficient independent multi-regime history/events',
                                         'Independent direction/strategy discrimination and calibrated target-first probabilities with realistic costs',
                                         'Sufficient genuine forward samples per frozen inference cohort'],
              'recovery_objectives': {'proposed_rpo_minutes': 30, 'proposed_rto_minutes': 60,
                                      'status': 'TARGETS_NOT_ACCEPTED_SLOS; off-host durability and cadence absent',
                                      'measured_scope': 'Local restore duration in phase3r_recovery_check.json; excludes host provisioning/transfer/secrets/cutover'},
              'new_market_models_trained': 0, 'new_independent_holdout_evaluations': 0,
              'promotion': 'NO_PROMOTION', 'trading_decision': 'NO_TRADE'}
    (ROOT / 'reports/phase3r_acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'decision': report['decision'], 'issued': forward['issued'], 'verified_matured': forward['verified_matured'],
                      'pending': forward['pending'], 'preservation': all(p['original_bytes_preserved'] for p in preservation)}))
    return 0 if all(p['original_bytes_preserved'] for p in preservation) else 1


if __name__ == '__main__':
    raise SystemExit(main())
