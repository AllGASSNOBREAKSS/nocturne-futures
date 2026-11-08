"""Acceptance must not disguise current integrity failures with old successes."""
import importlib.util
import json
from pathlib import Path

import pytest


@pytest.mark.parametrize('corrupt_model', [False, True])
def test_acceptance_retains_current_blockers_and_detects_preservation_failure(tmp_path, monkeypatch, corrupt_model):
    script = Path(__file__).resolve().parents[1] / 'scripts/phase3s_acceptance.py'
    spec = importlib.util.spec_from_file_location('phase3s_acceptance_fixture', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    monkeypatch.setattr(module.subprocess, 'check_output', lambda *a, **k: b'original')
    for name in ('data/shadow/ndx_range/forecasts.jsonl', 'data/shadow/ndx_range/outcomes.jsonl',
                 'models/shadow/ndx-range-v1/model.joblib'):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'changed' if corrupt_model and name.endswith('joblib') else b'original')
    reports = {
        'phase3i_forward.json': {'generated_at': '2026-11-08T08:00:00Z', 'issued': 4, 'verified_matured': 2,
                                'pending': 2, 'inference_samples': {},
                                'outcome_verification': {'status': 'VERIFIED_RESEARCH_GRADE'}},
        'phase3j_operations.json': {'status': 'degraded', 'issues': {'one': {}, 'two': {}},
                                  'open_alerts': [{}, {}]},
        'phase3s_scheduler_current.json': {'Status': 'DEGRADED'},
        'phase3s_encrypted_restore.json': {'result': {'status': 'RESTORED_NOT_ACTIVATED'}},
        'phase3s_ci.json': {'conclusion': 'success'},
        'phase3s_data_access.json': {'Status': 'USER_ACTION_REQUIRED'},
    }
    monkeypatch.setattr(module, 'read', lambda name: reports[name])
    (tmp_path / 'reports').mkdir()
    assert module.main() == (1 if corrupt_model else 0)
    result = json.loads((tmp_path / 'reports/phase3s_acceptance.json').read_text())
    assert result['decision'] == 'NO_GO_FRONTEND'
    assert result['percentage'] is None
    assert result['engineering']['forward_testing']['status'] == 'AUDIT_BLOCKED'
    assert result['engineering']['scheduler']['status'] == 'DEGRADED'
    assert result['engineering']['monitoring']['open_alert_count'] == 2
    assert result['forward']['pending'] == 2
    assert result['promotion'] == 'NO_PROMOTION'
    assert result['preservation'][-1]['original_bytes_preserved'] is not corrupt_model
