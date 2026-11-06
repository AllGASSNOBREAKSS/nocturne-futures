"""Collect security/recovery evidence; never activate services or promote models."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '504a168c455d945c42a5723a60c7d86236fcaadc'


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
              'decision': 'NO_GO_FRONTEND', 'percentage': None, 'preservation': preservation,
              'engineering': {
                  'api_authentication_authorization': {'status': 'COMPLETED_BOUNDED_TEST_SCOPE', 'evidence': 'tests/test_api_security.py'},
                  'api_limits_validation_audit': {'status': 'COMPLETED_SINGLE_PROCESS_SCOPE', 'evidence': 'tests/test_api_security.py'},
                  'tls': {'status': 'COMPLETED_ISOLATED_LOOPBACK_TEST', 'evidence': 'tests/test_tls_deployment.py', 'production_activation': 'NOT_PERFORMED'},
                  'scheduler': {'status': read('phase3s_scheduler.json')['Status'], 'evidence': 'reports/phase3s_scheduler.json', 'unattended_account': 'PREPARED_NOT_ACTIVATED'},
                  'backtesting_ml': {'status': 'COMPLETED_DEVELOPMENT_INFRASTRUCTURE_SCOPE', 'evidence': ['tests/test_daily_experiment.py', 'tests/test_backtest_regression.py'], 'new_market_fits': 0},
                  'forward_testing': {'status': forward['outcome_verification']['status'], 'evidence': 'reports/phase3i_forward.json'},
                  'data_artifact_integrity': {'status': 'COMPLETED_FROZEN_REPLAY_SCOPE', 'evidence': 'reports/phase3s_runtime.json'},
                  'deployment_reproducibility': {'status': 'COMPLETED_ISOLATED_ENVIRONMENT_SCOPE', 'evidence': ['reports/phase3s_runtime.json', 'reports/phase3s_dependency_lock.json']},
                  'encrypted_recovery': {'status': read('phase3s_encrypted_restore.json')['result']['status'], 'off_host': 'OFF_HOST_VERIFICATION_REQUIRED', 'evidence': ['reports/phase3s_encrypted_pack.json', 'reports/phase3s_encrypted_restore.json']},
                  'monitoring': {'status': 'PARTIAL', 'evidence': ['reports/phase3j_operations.json', 'docs/PHASE3S_SECURITY_DEPLOYMENT.md'], 'missing': 'Independent paging, backup/audit-capacity monitoring, long soak/reboot/logoff and hard process-memory isolation'},
                  'python_cpp_ci': {'status': read('phase3s_ci.json')['conclusion'], 'evidence': ['reports/phase3s_ci.json', 'reports/phase3s_tests.json']}
              },
              'quantitative': {
                  'authentic_futures_data': {'status': read('phase3s_data_access.json')['Status'], 'evidence': 'reports/phase3s_data_access.json'},
                  'historical_coverage': {'status': 'PARTIAL_INDEX_CONTEXT_NOT_LICENSED_FUTURES', 'evidence': 'docs/PHASE3R_FINDINGS.md'},
                  'direction_consolidation_levels_target_first': {'status': 'BLOCKED_INSUFFICIENT_AUTHENTIC_INDEPENDENT_PATHS_EVENTS_CALIBRATION', 'evidence': 'docs/PHASE3S_FINDINGS.md'},
                  'independent_validation': {'status': 'BLOCKED_NO_NEW_UNTOUCHED_EVALUATION', 'evidence': 'docs/architecture/model_validation.md'},
                  'genuine_forward_observations': {'status': 'PARTIAL_INSUFFICIENT_SAMPLE', 'cohorts': forward['inference_samples'], 'evidence': 'reports/phase3l_forward_audit.json'}
              },
              'forward': {key: forward[key] for key in ('generated_at', 'issued', 'verified_matured', 'pending', 'inference_samples', 'outcome_verification')},
              'open_user_actions': ['Configure production API credential files, certificate lifecycle and reviewed service/network ACLs; no public exposure authorized',
                                    'Approve/provide an unattended account/always-on host; verify reboot/logoff and independent monitoring',
                                    'Authorize independent encrypted backup destination and key custody; execute genuine off-host recovery and cutover/rollback',
                                    'Configure entitled GLBX.MDP3 access and approve exact per-request quotes before pilot consumption',
                                    'Accumulate adequate independent futures research and genuine forward observations before frontend/model promotion review'],
              'recovery_objectives': {'proposed_rpo_minutes': 30, 'proposed_rto_minutes': 60, 'status': 'PROPOSED_NOT_OFF_HOST_SLOS'},
              'promotion': 'NO_PROMOTION', 'trading_decision': 'NO_TRADE'}
    (ROOT / 'reports/phase3s_acceptance.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({'decision': report['decision'], 'issued': forward['issued'], 'verified_matured': forward['verified_matured'],
                      'pending': forward['pending'], 'original_bytes_preserved': all(p['original_bytes_preserved'] for p in preservation)}))
    return 0 if all(p['original_bytes_preserved'] for p in preservation) else 1


if __name__ == '__main__':
    raise SystemExit(main())
