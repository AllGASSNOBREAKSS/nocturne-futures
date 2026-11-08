"""Isolated synthetic lifecycle checks, never genuine forward observations."""
from datetime import datetime, timedelta, timezone
import importlib.util
from pathlib import Path

import pandas as pd
import pytest

from nocturne.shadow import ShadowStore, audit_forecasts, evaluate_matured, load_artifact
from nocturne.shadow.operations import assess_operations, monitor_operations
from nocturne.shadow.reconciliation import incident_disposition
from nocturne.shadow.service import health
from test_market_snapshots import evidence, capture
from test_shadow_service import bars

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2025, 3, 25, 2, 10, tzinfo=timezone.utc)


def runner(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location('phase3t_cycle_fixture', ROOT / 'scripts/phase3h_shadow.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, 'STORE_DIR', tmp_path / 'store')
    monkeypatch.setattr(module, 'LOCK_PATH', tmp_path / 'cycle.lock')
    monkeypatch.setattr(module, 'STATUS_PATH', tmp_path / 'status.json')
    monkeypatch.setattr(module, 'record_missed', lambda *a: [])
    artifact = load_artifact(ROOT / 'models/shadow', 'ndx-range-v1')
    monkeypatch.setattr(module, 'load_artifact', lambda *a: artifact)
    market = tmp_path / 'market'
    (market / 'manifests').mkdir(parents=True)
    import json
    for name in ('IDX_NDX', 'IDX_VIX'):
        (market / 'manifests' / f'{name}.json').write_text(json.dumps({'snapshot_id': 'fixture-only'}))
    monkeypatch.setattr(module, 'OPERATIONAL_DIR', market)
    # Existing relative-path interface expects source folders below ROOT.
    monkeypatch.setattr(module, 'ROOT', tmp_path)
    index, vix = bars(), bars(base=20, step=0)
    monkeypatch.setattr(module, 'load_bars', lambda symbol, now: (index if symbol == '^NDX' else vix, str(market)))
    return module


def test_incident_report_is_not_reconciliation_or_finality_authority(tmp_path):
    archive, store, _, forecast = evidence(tmp_path)
    revised = capture(archive, revision=True, received='2025-03-25T02:00Z')
    before = store.forecast_path.read_bytes()
    result = incident_disposition(forecast, archive, revised, NOW,
                                  [{'status': 'CURRENT_CLOSE_OBSERVED', 'verified': True}])
    assert result['verdict'] == 'AUDIT_BLOCKED'
    assert result['eligible_for_evaluation'] is False
    assert result['reconciliation_applied'] is False
    assert result['difference_points'] == result['revised_reference_close'] - result['original_reference_close']
    assert result['provider_revision_evidence']['issuance_features_exactly_reproduced']
    assert not result['outcome_observation']['time_bound_elapsed']
    assert store.forecast_path.read_bytes() == before
    assert store.reconciliations() == [] and store.outcomes() == []


def test_elapsed_time_and_same_provider_bar_do_not_establish_independent_outcome(tmp_path):
    archive, _, _, forecast = evidence(tmp_path)
    revised = capture(archive, revision=True, received='2025-03-25T02:00Z')
    result = incident_disposition(forecast, archive, revised, NOW + timedelta(days=2))
    assert result['outcome_observation']['time_bound_elapsed']
    assert not result['eligible_for_evaluation']
    assert 'INDEPENDENT_FINAL_OUTCOME_OHLC_NOT_VERIFIED' in result['blocking_reasons']


def test_corrupt_issuance_cannot_be_reclassified_as_benign_provider_revision(tmp_path):
    archive, _, _, forecast = evidence(tmp_path)
    revised = capture(archive, revision=True, received='2025-03-25T02:00Z')
    with pytest.raises(ValueError, match='sealed'):
        incident_disposition({**forecast, 'reference_close': 1.0}, archive, revised, NOW)


@pytest.mark.parametrize('revert_close', [False, True])
def test_strict_bar_proof_cannot_fall_back_to_old_close_only_proof(tmp_path, revert_close):
    from nocturne.shadow.reconciliation import investigate_revision
    archive, store, _, forecast = evidence(tmp_path)
    revised = capture(archive, revision=True, received='2025-03-25T02:00Z')
    proof = investigate_revision(forecast, archive, revised, NOW)['record']
    # Historical compatibility proof precedes the upgraded strict one.
    legacy = {k: v for k, v in proof.items() if k != 'revised_reference_bar_sha256'}
    store.append_reconciliation(legacy)
    store.append_reconciliation(proof)
    frame = archive.frame(revised)
    assert not audit_forecasts(store, frame, snapshot_root=archive.root)['failed']
    changed = frame.copy()
    changed.loc[changed.date == forecast['data_date'], 'volume'] += 1
    if revert_close:
        changed.loc[changed.date == forecast['data_date'], 'close'] = forecast['reference_close']
    assert audit_forecasts(store, changed, snapshot_root=archive.root)['failed']
    assert not store.outcomes()


def test_future_issue_proceeds_while_older_forecast_is_quarantined_and_retry_is_idempotent(tmp_path, monkeypatch):
    module = runner(tmp_path, monkeypatch)
    store = ShadowStore(module.STORE_DIR)
    from test_shadow_operations import forecast
    store.append_forecast(forecast(identifier='older-quarantined', target='2025-03-24'))
    original = store.forecast_path.read_bytes()
    failed = {'forecast_id': 'older-quarantined', 'issues': ['REFERENCE_CLOSE_MISMATCH']}
    monkeypatch.setattr(module, 'audit_forecasts', lambda *a, **k: {'failed': [failed], 'records': []})
    first = module.cycle(False, now=NOW)
    assert first['generation'] == 'STORED'
    assert first['execution_status'] == 'COMPLETED'
    assert first['operational_status'] == 'AUDIT_BLOCKED'
    assert first['quarantined_forecast_ids'] == ['older-quarantined']
    second = module.cycle(False, now=NOW)
    assert second['generation'] == 'ALREADY_ISSUED'
    assert len(store.forecasts()) == 2
    assert store.forecast_path.read_bytes().startswith(original)
    assert not store.outcomes()
    assert module.acquire_lock()
    module.release_lock()


def test_generation_failure_is_not_masked_by_historical_quarantine(tmp_path, monkeypatch):
    module = runner(tmp_path, monkeypatch)
    monkeypatch.setattr(module, 'generate', lambda *a, **k: {'status': 'SKIPPED', 'reason': 'STALE_VIX'})
    monkeypatch.setattr(module, 'audit_forecasts', lambda *a, **k: {'failed': [{'forecast_id': 'old'}], 'records': []})
    result = module.cycle(False, now=NOW)
    assert result['operational_status'] == 'CYCLE_FAILED'
    assert result['evaluation_integrity_status'] == 'QUARANTINED'
    assert ShadowStore(module.STORE_DIR).log_events()[-1]['event'] == 'CYCLE_FAILED'


def test_quarantine_does_not_prevent_unrelated_available_outcome(tmp_path):
    from test_shadow_operations import forecast
    store = ShadowStore(tmp_path)
    store.append_forecast(forecast(identifier='bad', target='2025-03-24'))
    store.append_forecast(forecast(identifier='good', target='2025-03-25'))
    index = pd.DataFrame([{'date': '2025-03-25', 'timestamp': '2025-03-25T13:30Z',
                           'available_at': '2025-03-26T00:00Z', 'open': 100., 'high': 103.,
                           'low': 99., 'close': 102., 'volume': 1., 'source_complete': True}])
    now = NOW + timedelta(days=1)
    assert [o['forecast_id'] for o in evaluate_matured(store, index, now, {'good'})] == ['good']
    assert evaluate_matured(ShadowStore(tmp_path), index, now, {'good'}) == []
    assert {o['forecast_id'] for o in store.outcomes()} == {'good'}


def test_fresh_quarantine_is_completed_execution_not_healthy_integrity(tmp_path):
    store = ShadowStore(tmp_path)
    store.log('CYCLE_OK', now=NOW - timedelta(days=3))
    store.log('CYCLE_AUDIT_FAILED', now=NOW)
    result = health(store, NOW)
    assert result['cycle_execution_status'] == 'COMPLETED' and result['status'] == 'degraded'
    assert 'STALE_SERVICE' not in result['warnings']
    assert 'STALE_FULLY_HEALTHY_CYCLE' in result['warnings']
    status = {'generated_at': NOW.isoformat(), 'operational_status': 'AUDIT_BLOCKED', 'generation': 'ALREADY_ISSUED',
              'audit': {'failed': [{'forecast_id': 'old'}]}}
    state = assess_operations(store, status, NOW)
    assert state['components']['service_execution']['status'] == 'COMPLETED_WITH_QUARANTINE'
    assert state['components']['forecast_issuance']['status'] == 'ISSUED'
    assert state['components']['forecast_integrity']['status'] == 'BLOCKED'
    assert state['components']['outcome_evaluation']['status'] == 'PARTIAL_QUARANTINE'
    assert health(store, NOW + timedelta(hours=2))['cycle_execution_status'] == 'STALE'


def test_acknowledgement_never_hides_or_resolves_an_open_incident(tmp_path):
    store = ShadowStore(tmp_path)
    status = {'generated_at': NOW.isoformat(), 'operational_status': 'AUDIT_BLOCKED',
              'audit': {'failed': [{'forecast_id': 'old'}]}}
    report = monitor_operations(store, status, NOW)
    key = 'FORECAST_AUDIT:old'
    event = store.acknowledge_alert(key, 'operator', 'INVESTIGATING', NOW)
    assert event['state'] == 'OPEN' and event['event'] == 'ACKNOWLEDGED'
    count = len(store.alert_events())
    assert store.acknowledge_alert(key, 'operator', 'INVESTIGATING', NOW) == event
    assert len(store.alert_events()) == count
    assert any(a['key'] == key for a in monitor_operations(ShadowStore(tmp_path), status, NOW)['open_alerts'])
    assert len(report['open_alerts']) == len(monitor_operations(store, status, NOW)['open_alerts'])
    recovered = monitor_operations(store, {**status, 'operational_status': 'SHADOW_ACTIVE', 'audit': {'failed': []}}, NOW)
    assert not recovered['open_alerts']
    assert any(a.get('event') == 'ACKNOWLEDGED' for a in store.alert_events())
    with pytest.raises(ValueError, match='open alert'):
        store.acknowledge_alert(key, 'operator', 'INVESTIGATING', NOW)


@pytest.mark.parametrize('actor,reason', [('operator secret', 'CHECK'), ('operator', 'free text'), ('x'*65, 'CHECK')])
def test_acknowledgements_accept_only_bounded_identifiers_and_reason_codes(tmp_path, actor, reason):
    with pytest.raises(ValueError):
        ShadowStore(tmp_path).acknowledge_alert('unknown', actor, reason, NOW)


def quarantine_receipt(kind='SHADOW_FORECAST'):
    return {'execution_status': 'COMPLETED', 'operational_status': 'AUDIT_BLOCKED',
            'generation': 'ALREADY_ISSUED' if kind == 'SHADOW_FORECAST' else 'EVALUATE_ONLY',
            'audit': {'failed': [{'forecast_id': 'old'}]}, 'quarantined_forecast_ids': ['old'],
            'evaluation_integrity_status': 'QUARANTINED', 'matured_now': 0,
            'refresh': {s: {'status': 'FETCHED'} for s in ('^NDX', '^VIX')}}


@pytest.mark.parametrize('kind', ['DATA_REFRESH', 'SHADOW_FORECAST', 'FORECAST_MATURITY_CHECK'])
def test_scoped_completion_with_quarantine_keeps_failure_evidence_in_job_health(kind):
    from nocturne.research.jobs import assess_shadow_receipt
    from nocturne.research.health import assess_jobs
    result = assess_shadow_receipt(kind, 1, quarantine_receipt(kind))
    assert result['status'] == 'SUCCEEDED'
    assert result['exit_code'] == 1 and result['integrity_status'] == 'AUDIT_BLOCKED'
    job = {'id': 'fixture', 'created': NOW.timestamp(), 'updated': NOW.timestamp(), 'timeout': 60,
           'lane': 'shadow', 'kind': kind, 'state': 'SUCCEEDED', 'payload': {}, 'result': result}
    assert assess_jobs([job], NOW)['counts'] == {'BLOCKED': 1}


@pytest.mark.parametrize('failure', ['exception', 'issuance', 'missing-seal', 'wrong-exit', 'refresh'])
def test_nonzero_job_is_not_forgiven_without_exact_scoped_completion(failure):
    from nocturne.research.jobs import assess_shadow_receipt
    receipt = quarantine_receipt()
    kind, exit_code = 'SHADOW_FORECAST', 1
    if failure == 'exception':
        receipt['execution_status'] = 'FAILED'
    elif failure == 'issuance':
        receipt['generation'] = 'SKIPPED'
        receipt['generation_detail'] = {'reason': 'STALE_VIX'}
    elif failure == 'missing-seal':
        receipt.pop('quarantined_forecast_ids')
    elif failure == 'wrong-exit':
        exit_code = 75
    else:
        kind = 'DATA_REFRESH'
        receipt = quarantine_receipt(kind)
        receipt['refresh']['^NDX']['status'] = 'FETCH_FAILED'
    assert assess_shadow_receipt(kind, exit_code, receipt)['status'] != 'SUCCEEDED'


def test_job_uses_exclusive_attempt_receipt_not_shared_status(tmp_path, monkeypatch):
    import json
    from types import SimpleNamespace
    import nocturne.research.jobs as jobs
    shared = tmp_path / 'reports/phase3h_shadow_status.json'
    shared.parent.mkdir()
    shared.write_text(json.dumps(quarantine_receipt()))
    attempt = tmp_path / 'attempt'
    attempt.mkdir()
    def absent(command, **kwargs):
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(jobs.subprocess, 'run', absent)
    failed = jobs.execute_job('SHADOW_FORECAST', {}, tmp_path, attempt, None, {'lane': 'shadow'})
    assert failed['status'] == 'FAILED' and failed['reason'] == 'SHADOW_ATTEMPT_RECEIPT_INVALID'
    def completed(command, **kwargs):
        path = Path(command[command.index('--receipt-file') + 1])
        with path.open('x') as handle:
            json.dump(quarantine_receipt(), handle)
        return SimpleNamespace(returncode=1)
    monkeypatch.setattr(jobs.subprocess, 'run', completed)
    result = jobs.execute_job('SHADOW_FORECAST', {}, tmp_path, attempt, None, {'lane': 'shadow'})
    assert result['status'] == 'SUCCEEDED' and result['integrity_status'] == 'AUDIT_BLOCKED'
    assert len(result['receipt_sha256']) == 64


def test_one_shot_lock_contention_returns_75_and_cannot_overwrite_receipt(tmp_path, monkeypatch):
    import json
    import sys
    module = runner(tmp_path, monkeypatch)
    receipt = tmp_path / 'attempt.json'
    monkeypatch.setattr(module, 'cycle', lambda *a, **k: {'status': 'LOCKED'})
    monkeypatch.setattr(sys, 'argv', ['phase3h_shadow.py', '--once', '--receipt-file', str(receipt)])
    assert module.main() == 75
    before = receipt.read_bytes()
    assert json.loads(before)['status'] == 'LOCKED'
    with pytest.raises(SystemExit):
        module.main()
    assert receipt.read_bytes() == before
