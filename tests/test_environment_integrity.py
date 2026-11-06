"""Integrity fixtures plus replay of immutable issued rows; not new market fits."""
import base64
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from nocturne.runtime_integrity import exact_pins, file_hash, verify_wheelhouse, verify_installed, verify_frozen_inference
from nocturne.shadow import load_artifact

ROOT = Path(__file__).resolve().parents[1]


def test_capture_admission_defers_at_real_collision_boundary():
    from datetime import datetime, timezone
    from nocturne.runtime_integrity import check_capture_window
    now = datetime(2026, 11, 6, 1, 46, 58, tzinfo=timezone.utc)
    with pytest.raises(BlockingIOError, match='scheduled tick'):
        check_capture_window(now, ['2026-11-06T01:47:06+00:00'], 30)
    assert check_capture_window(now, ['2026-11-06T02:17:06+00:00'], 30)['status'] == 'CAPTURE_WINDOW_CHECKED'
    with pytest.raises(ValueError, match='30-second'):
        check_capture_window(now, ['2026-11-06T02:17:06+00:00'], 60)


def test_bootstrap_integrity_module_needs_no_installed_dependencies():
    import os
    import subprocess
    import sys
    result = subprocess.run([sys.executable, '-S', '-c',
                             "import sys,nocturne.runtime_integrity; assert not any(n in sys.modules for n in ('numpy','pandas','sklearn'))"],
                            env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')}, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr


def test_ci_workflow_parses_and_includes_locked_runtime_job():
    import yaml
    workflow = yaml.safe_load((ROOT / '.github/workflows/ci.yml').read_text())
    assert {'python', 'typescript', 'native', 'windows-shadow', 'windows-locked-runtime'} <= set(workflow['jobs'])
    for job in workflow['jobs'].values():
        for step in job['steps']:
            if 'run' in step:
                assert isinstance(step['run'], str)


def test_real_frozen_model_reproduces_both_issued_cohorts_exactly():
    artifact = load_artifact(ROOT / 'models/shadow', 'ndx-range-v1')
    forecasts = [json.loads(line) for line in (ROOT / 'data/shadow/ndx_range/forecasts.jsonl').read_text().splitlines()]
    before = (ROOT / 'models/shadow/ndx-range-v1/model.joblib').read_bytes()
    result = verify_frozen_inference(artifact, forecasts)
    assert {r['inference_revision'] for r in result['records']} == {'legacy-unadjusted', 'residual-adjusted-v1'}
    assert len(result['records']) == len(forecasts)
    assert (ROOT / 'models/shadow/ndx-range-v1/model.joblib').read_bytes() == before


@pytest.mark.parametrize('change', ['quantile', 'cohort', 'identity', 'duplicate', 'empty'])
def test_inference_drift_or_unknown_identity_blocks(change):
    artifact = load_artifact(ROOT / 'models/shadow', 'ndx-range-v1')
    forecasts = [json.loads((ROOT / 'data/shadow/ndx_range/forecasts.jsonl').read_text().splitlines()[0])]
    if change == 'quantile':
        import math
        forecasts[0]['quantiles']['p50'] = math.nextafter(forecasts[0]['quantiles']['p50'], 1.0)
    elif change == 'cohort':
        forecasts[0]['inference_revision'] = 'unreviewed-upgrade'
    elif change == 'identity':
        forecasts[0]['model_version'] = 'wrong'
    elif change == 'duplicate':
        forecasts *= 2
    else:
        forecasts = []
    with pytest.raises(ValueError):
        verify_frozen_inference(artifact, forecasts)


def test_only_exact_unique_pins_are_accepted(tmp_path):
    lock = tmp_path / 'pins.txt'
    lock.write_text('# fixture\nExample_Package==1.2.3\n')
    assert exact_pins([lock]) == {'example-package': '1.2.3'}
    for invalid in ('numpy>=1.0', '-r other.txt', 'x==1\nx==1', '# empty', 'x==1; python_version>="3"'):
        lock.write_text(invalid)
        with pytest.raises(ValueError):
            exact_pins([lock])


@pytest.mark.parametrize('change', ['bytes', 'extra', 'missing', 'duplicate', 'upstream', 'escape'])
def test_wheelhouse_drift_is_rejected(tmp_path, change):
    wheel = tmp_path / 'example-1-py3-none-any.whl'
    wheel.write_bytes(b'synthetic wheel bytes, never installed')
    entry = {'name': 'example', 'version': '1', 'filename': wheel.name, 'bytes': wheel.stat().st_size,
             'sha256': file_hash(wheel), 'pypi_sha256': file_hash(wheel)}
    manifest = {'target': 'windows-x86_64-cpython-314', 'wheels': [entry]}
    assert verify_wheelhouse(tmp_path, manifest, {'example': '1'})['wheels'] == 1
    if change == 'bytes':
        wheel.write_bytes(b'corrupted')
    elif change == 'extra':
        (tmp_path / 'extra.whl').write_bytes(b'fixture')
    elif change == 'missing':
        wheel.unlink()
    elif change == 'duplicate':
        manifest['wheels'].append(deepcopy(entry))
    elif change == 'upstream':
        entry['pypi_sha256'] = '0' * 64
    else:
        entry['filename'] = '../escape.whl'
    with pytest.raises(ValueError):
        verify_wheelhouse(tmp_path, manifest, {'example': '1'})


def test_installed_record_corruption_version_and_prefix_fail(monkeypatch, tmp_path):
    from importlib.metadata import PackagePath
    payload = tmp_path / 'payload.py'
    payload.write_bytes(b'original fixture')
    item = PackagePath('payload.py')
    item.hash = SimpleNamespace(mode='sha256', value=base64.urlsafe_b64encode(hashlib.sha256(payload.read_bytes()).digest()).decode().rstrip('='))
    item.size = payload.stat().st_size
    distribution = SimpleNamespace(version='1', files=[item], locate_file=lambda f: tmp_path / str(f))
    monkeypatch.setattr('nocturne.runtime_integrity.metadata.distribution', lambda n: distribution)
    assert verify_installed({'fixture': '1'}, tmp_path)['files'] == 1
    with pytest.raises(ValueError, match='version'):
        verify_installed({'fixture': '2'}, tmp_path)
    with pytest.raises(ValueError, match='prefix'):
        verify_installed({'fixture': '1'}, tmp_path / 'different')
    payload.write_bytes(b'corrupted fixture')
    with pytest.raises(ValueError, match='RECORD'):
        verify_installed({'fixture': '1'}, tmp_path)
