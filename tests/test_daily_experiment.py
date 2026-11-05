import numpy as np
import pandas as pd
import pytest

from nocturne.research.daily_experiment import build_dataset, folds, FEATURES, context_backtest, verified_history


def history(count=2500):
    stamps = pd.date_range("2000-01-03T14:30Z", periods=count, freq="B")
    price = 100 + np.arange(count) * .02 + np.sin(np.arange(count))
    return pd.DataFrame({"date": stamps.strftime("%Y-%m-%d"), "timestamp": stamps,
                         "available_at": stamps.normalize() + pd.Timedelta("1D"), "open": price,
                         "high": price + 2, "low": price - 2, "close": price + np.cos(np.arange(count)) * .5,
                         "volume": 100, "source_complete": True})


def test_missing_final_label_and_holdout_never_enter_development():
    raw = history(7500)
    data = build_dataset(raw)
    assert data.label_end.max() < pd.Timestamp("2024-01-01", tz="UTC")
    assert raw.date.iloc[-1] not in data.date.tolist()
    assert (data.feature_available_at < data.entry_time).all()


def test_features_are_invariant_to_unseen_future_prices():
    raw = history()
    before = build_dataset(raw)
    raw.loc[raw.index > 500, ["open", "high", "low", "close"]] *= 3
    after = build_dataset(raw)
    pd.testing.assert_frame_equal(before.iloc[:479][FEATURES], after.iloc[:479][FEATURES])


def test_walk_forward_purges_labels_and_keeps_calibration_separate():
    parts = folds(build_dataset(history()))
    assert parts
    for fold in parts:
        assert fold.train.label_end.max() + pd.Timedelta("5D") < fold.calibration.feature_available_at.min()
        assert fold.calibration.label_end.max() + pd.Timedelta("5D") < fold.test.feature_available_at.min()
        assert set(fold.train.signal_id).isdisjoint(fold.test.signal_id)


def test_context_backtest_does_not_claim_futures_pnl_or_barrier_events():
    result = context_backtest(build_dataset(history(100)))
    assert result["target_first"] is None and result["mfe_mae"] is None
    assert result["scope"].startswith("NON_EXECUTABLE")
    assert result["sensitivity"]["5"]["net_mean_fraction"] < result["sensitivity"]["0"]["net_mean_fraction"]


def test_incomplete_sources_cannot_be_imputed_as_available_features():
    raw = history(100)
    raw.loc[50, "source_complete"] = False
    data = build_dataset(raw)
    assert raw.date.iloc[50] not in data.date.tolist()


def test_receipt_hash_mismatch_blocks_before_research(tmp_path):
    import json
    (tmp_path / "manifests").mkdir()
    (tmp_path / "raw").mkdir()
    (tmp_path / "manifests/IDX_NDX.json").write_text(json.dumps({"raw_sha256": "missing", "normalized_sha256": "bad"}))
    with pytest.raises(ValueError, match="checksum"):
        verified_history(tmp_path, "^NDX")


def test_logistic_and_calibration_are_reproducible_on_fixed_protocol(tmp_path):
    from nocturne.research.daily_experiment import train_development, evaluate_development
    data = build_dataset(history())
    left, right = tmp_path / "left", tmp_path / "right"
    a = train_development(data, left)
    b = train_development(data, right)
    ra, pa = evaluate_development(data, left, a)
    rb, pb = evaluate_development(data, right, b)
    pd.testing.assert_frame_equal(pa, pb)
    assert ra == rb
    assert ra["decision"] == "NO_PROMOTION" and ra["holdout_scored"] is False
    artifact = left / "fold_0.joblib"
    artifact.write_bytes(b"corrupted fixture")
    with pytest.raises(ValueError, match="artifact changed"):
        evaluate_development(data, left, a)


def test_training_cache_reuses_identity_and_rejects_changed_artifacts(tmp_path, monkeypatch):
    import json
    from pathlib import Path
    from nocturne.research.orchestrator import JobStore
    from nocturne.research.jobs import execute_job
    from nocturne.adapters.snapshots import digest
    import nocturne.research.jobs as jobs
    root = Path(__file__).resolve().parents[1]
    store = JobStore(tmp_path / "state")
    feature = store.submit("FEATURE_BUILD", "research", "fixture", {"symbol": "^NDX"})
    path = tmp_path / "fixture.csv"
    build_dataset(history()).to_csv(path, index=False)
    store.transition(feature, "SUCCEEDED", {"dataset_path": str(path), "dataset_sha256": digest(path.read_bytes()), "symbol": "^NDX"})
    identifier = store.submit("MODEL_TRAINING", "research", "fixture", dependencies=[feature])
    job = next(j for j in store.jobs() if j["id"] == identifier)
    calls = []
    def fit(data, destination):
        calls.append(destination)
        destination.mkdir()
        (destination / "fold_0.joblib").write_bytes(b"fixture-model-not-market")
        return [{"fold": 0, "model_sha256": digest(b"fixture-model-not-market")}]
    monkeypatch.setattr(jobs, "train_development", fit)
    a = execute_job("MODEL_TRAINING", {}, root, tmp_path, store, job)
    b = execute_job("MODEL_TRAINING", {}, root, tmp_path, store, job)
    assert a["experiment_id"] == b["experiment_id"] and len(calls) == 1
    assert b["reused_without_retraining"] is True
    (Path(a["destination"]) / "fold_0.joblib").write_bytes(b"changed")
    with pytest.raises(ValueError, match="corrupted"):
        execute_job("MODEL_TRAINING", {}, root, tmp_path, store, job)
