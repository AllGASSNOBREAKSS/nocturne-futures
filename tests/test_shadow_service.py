import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nocturne.api.app import create_app
from nocturne.api.service import ForecastService
from nocturne.shadow import (ShadowStore, assess_eligibility, evaluate_matured,
                             evaluation_summary, forecast_id, generate, load_artifact)
from nocturne.shadow.features import FEATURES, build_features, build_history

UTC = timezone.utc
ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "ndx-range-v1"


def bars(start="2024-01-02", periods=320, step=1.0, base=100.0):
    dates = pd.bdate_range(start, periods=periods)
    close = base + pd.Series(range(periods), index=dates) * step
    return pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "timestamp": dates.tz_localize("UTC"),
        "available_at": (dates + pd.Timedelta(days=1)).tz_localize("UTC"),
        "open": close.to_numpy(), "high": (close + 1).to_numpy(),
        "low": (close - 1).to_numpy(), "close": close.to_numpy(),
        "volume": 1000.0,
    })


def test_features_ignore_bars_not_yet_available():
    index = bars()
    vix = bars(base=20.0, step=0.0)
    asof = pd.Timestamp("2025-01-15T12:00Z")
    first = build_features(index, vix, asof)
    changed = index.copy()
    mask = pd.to_datetime(changed.date) >= pd.Timestamp("2025-01-15")
    changed.loc[mask, ["open", "high", "low", "close"]] += 500
    second = build_features(changed, vix, asof)
    assert first.values == second.values
    assert set(first.values) == set(FEATURES)


def test_history_labels_use_next_session_only():
    index = bars()
    vix = bars(base=20.0, step=0.0)
    history = build_history(index, vix)
    row = history.dropna(subset=["next_range_pct"]).iloc[0]
    position = history.index[history.date == row.date][0]
    expected = (index.high.iloc[position + 1] - index.low.iloc[position + 1]) / index.close.iloc[position]
    assert abs(row.next_range_pct - expected) < 1e-12


def test_eligibility_rejects_stale_and_open_sessions():
    index = bars()
    vix = bars(base=20.0, step=0.0)
    last = pd.to_datetime(index.date.iloc[-1])
    target = pd.Timestamp("2025-03-25")
    now = datetime(2025, 3, 25, 1, 0, tzinfo=UTC)
    good = assess_eligibility(index, vix, now)
    assert good["eligible"] is True, good
    assert good["target_date"] == target.date().isoformat()
    # Running after the target session opens is too late.
    late = assess_eligibility(index, vix, datetime(2025, 3, 25, 15, 0, tzinfo=UTC))
    assert late["eligible"] is False and late["reason"] == "TOO_LATE_FOR_TARGET"
    # Missing the most recent session is stale, not eligible.
    stale = assess_eligibility(index.iloc[:-1], vix, now)
    assert stale["eligible"] is False and stale["reason"] == "STALE_DATA_DATE"
    # Stale VIX context fails closed.
    old_vix = vix.copy()
    old_vix["date"] = (pd.to_datetime(old_vix.date) - pd.Timedelta(days=20)).dt.strftime("%Y-%m-%d")
    old_vix["available_at"] = pd.to_datetime(old_vix.available_at) - pd.Timedelta(days=20)
    assert assess_eligibility(index, old_vix, now)["reason"] == "STALE_VIX"


def test_store_is_immutable_and_idempotent(tmp_path):
    store = ShadowStore(tmp_path)
    record = {"forecast_id": "abc", "model_id": MODEL_ID, "target_date": "2026-01-05",
              "data_date": "2026-01-02", "created_at": "2026-01-02T01:00:00+00:00",
              "quantiles": {"p50": 0.01, "p80": 0.02, "p90": 0.03},
              "features": {}, "feature_digest": "d"}
    store.append_forecast(record)
    store.append_forecast({**record, "created_at": "2026-01-02T02:00:00+00:00"})
    assert len(store.forecasts()) == 1
    with pytest.raises(ValueError, match="conflicting"):
        store.append_forecast({**record, "quantiles": {"p50": 0.02, "p80": 0.03, "p90": 0.04}})
    outcome = {"forecast_id": "abc", "evaluated_at": "2026-01-06T00:00:00+00:00",
               "realized_range_pct": 0.015, "covered": {"p50": True, "p80": True, "p90": True}}
    store.append_outcome(outcome)
    assert len(store.outcomes()) == 1
    with pytest.raises(ValueError, match="conflicting outcome"):
        store.append_outcome({**outcome, "realized_range_pct": 0.02})


def test_generate_and_evaluate_end_to_end(tmp_path):
    artifact = load_artifact(ROOT / "models/shadow", MODEL_ID)
    index = bars()
    vix = bars(base=20.0, step=0.0)
    store = ShadowStore(tmp_path)
    now = datetime(2025, 3, 25, 1, 0, tzinfo=UTC)
    result = generate(artifact, store, index, vix, now, validation_status="RESEARCH_VALIDATED_PENDING_SHADOW")
    assert result["status"] == "STORED", result
    forecast = store.latest()
    assert forecast["quantiles"]["p50"] <= forecast["quantiles"]["p80"] <= forecast["quantiles"]["p90"]
    assert forecast["trading_decision"] == "NO_TRADE"
    assert forecast["target_date"] == "2025-03-25"
    # Idempotent retry keeps a single record.
    generate(artifact, store, index, vix, now, validation_status="RESEARCH_VALIDATED_PENDING_SHADOW")
    assert len(store.forecasts()) == 1
    # Before maturity nothing is written.
    assert evaluate_matured(store, index, now) == []
    assert evaluation_summary(store)["matured"] == 0
    extra = pd.DataFrame([{"date": "2025-03-25", "timestamp": pd.Timestamp("2025-03-25", tz="UTC"),
                           "available_at": pd.Timestamp("2025-03-26", tz="UTC"),
                           "open": 100.0, "high": 102.0, "low": 98.0, "close": 101.0, "volume": 1.0}])
    later = datetime(2025, 3, 26, 2, 0, tzinfo=UTC)
    written = evaluate_matured(store, pd.concat([index, extra], ignore_index=True), later)
    assert written
    summary = evaluation_summary(store)
    assert summary["matured"] == 1
    assert 0 <= summary["coverage"]["p90"] <= 1
    # A second evaluation must not duplicate the outcome.
    evaluate_matured(store, pd.concat([index, extra], ignore_index=True), later)
    assert len(store.outcomes()) == 1


def test_frozen_artifact_reproduces_reported_holdout():
    metadata = json.loads((ROOT / "models/shadow" / MODEL_ID / "metadata.json").read_text())
    stored = json.loads((ROOT / "reports/phase3g_daily_range.json").read_text())["final_holdout"]
    assert metadata["validation_status"] == "RESEARCH_VALIDATED_PENDING_SHADOW"
    assert metadata["trading_decision"] == "NO_TRADE"
    for key, quantile in (("p50", "0.5"), ("p80", "0.8"), ("p90", "0.9")):
        expected = stored["quantiles"][quantile]
        assert abs(metadata["holdout_reproduced"][key]["coverage"] - expected["coverage"]) < 1e-9
        assert abs(metadata["holdout_reproduced"][key]["pinball_loss"] - expected["pinball_loss"]) < 1e-9
    assert metadata["scope"].startswith("Nasdaq-100 cash-session")


def test_api_exposes_shadow_endpoints_read_only(tmp_path):
    service = ForecastService(journal_root=tmp_path / "journal", registry_root=tmp_path / "registry",
                              forecast_root=tmp_path / "forecasts")
    client = TestClient(create_app(service))
    for path in ("/v1/shadow/ndx-range", "/v1/shadow/history", "/v1/shadow/evaluation", "/v1/data/health"):
        response = client.get(path)
        assert response.status_code == 200
        assert "NO_TRADE" in response.text or "trading_decision" in response.text or "status" in response.text
    assert client.get("/v1/shadow/history?limit=0").status_code == 422
