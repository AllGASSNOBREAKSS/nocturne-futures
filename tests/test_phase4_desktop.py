"""Phase 4 desktop backend: security boundary, causality, job flow and immutability."""
import json
import secrets

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from nocturne.desktop_server import create_app
from nocturne.studio import backtest, forecasts, indicators, jobs, market, rules, training


@pytest.fixture(scope="module")
def client():
    token = secrets.token_urlsafe(32)
    c = TestClient(create_app(token), base_url="http://127.0.0.1")
    c.headers["Authorization"] = f"Bearer {token}"
    return c


def test_token_required_and_mutations_are_allow_listed(client):
    anonymous = TestClient(client.app, base_url="http://127.0.0.1")
    assert anonymous.get("/v1/system/health").status_code == 401
    wrong = TestClient(client.app, base_url="http://127.0.0.1", headers={"Authorization": "Bearer " + "x" * 43})
    assert wrong.get("/v1/system/health").status_code == 401
    assert client.get("/v1/system/health").json()["broker_execution"] is False
    assert client.post("/v1/levels/NQ").status_code == 405  # not an allow-listed mutation
    assert client.post("/v1/markets/NQ/bars").status_code == 405
    with pytest.raises(ValueError):
        create_app("short")


def test_default_public_api_stays_read_only():
    from nocturne.api.app import create_app as public_app
    from nocturne.api.security import SecurityPolicy
    app = public_app(security=SecurityPolicy.internal(), audit=lambda record: None)
    c = TestClient(app)
    assert c.post("/v1/backtests").status_code == 405


def test_responses_are_strict_json(client):
    for path in ("/v1/intel", "/v1/research", "/v1/forecasts/ndx-shadow", "/v1/operations"):
        r = client.get(path)
        assert r.status_code == 200, path
        json.loads(r.text, parse_constant=lambda c: pytest.fail(f"non-finite number in {path}"))
    shadow = client.get("/v1/forecasts/ndx-shadow").json()
    assert {"forecasts", "outcomes", "quarantined"} <= set(shadow)


def test_bars_are_available_only_after_they_close():
    frame, _ = market.bars("NQ", "5m", limit=50, source="yahoo")
    assert ((frame.available_at - frame.timestamp) == pd.Timedelta("5min")).all()
    daily, _ = market.bars("NQ", "15m", limit=20)
    assert ((daily.available_at - daily.timestamp) == pd.Timedelta("15min")).all()


@pytest.mark.parametrize("name,params", [("sma", {"n": 20}), ("ema", {"n": 20}), ("rsi", {"n": 14}), ("atr", {"n": 14}),
                                         ("adx", {"n": 14}), ("vwap", {}), ("macd_hist", {}), ("bb_upper", {}), ("swing_high", {"n": 3})])
def test_indicators_never_use_future_bars(name, params):
    frame, _ = market.bars("NQ", "5m", limit=600)
    full = indicators.compute(frame, name, params)
    cut = 400
    truncated = indicators.compute(frame.iloc[:cut].copy(), name, params)
    a, b = full.iloc[:cut].to_numpy(float), truncated.to_numpy(float)
    both = ~np.isnan(a) & ~np.isnan(b)
    assert np.allclose(a[both], b[both], rtol=1e-9, atol=1e-9)
    assert (np.isnan(a) == np.isnan(b)).mean() > 0.99


def test_indicator_parameter_bounds_are_enforced():
    frame, _ = market.bars("NQ", "5m", limit=100)
    with pytest.raises(ValueError):
        indicators.compute(frame, "rsi", {"n": 5000})
    with pytest.raises(ValueError):
        indicators.compute(frame, "cvd")


def test_rule_validation_and_next_bar_entry():
    assert rules.validate({"side": "UP"})
    good = {"side": "LONG", "conditions": [{"left": {"indicator": "close"}, "op": ">", "right": {"indicator": "sma", "params": {"n": 20}}}],
            "stop": {"type": "points", "value": 20}, "targets_r": [1, 2], "horizon_bars": 12, "session": "ETH", "max_trades_per_session": 2}
    assert rules.validate(good) == []
    frame, _ = market.bars("NQ", "5m", limit=800)
    from nocturne.instruments import get_instrument
    signals = rules.RuleStrategy(good).signals(frame, get_instrument("NQ"))
    assert signals
    stamps = set(frame.timestamp)
    for _, s in signals[:50]:
        i = s.metadata["bar_index"]
        assert pd.Timestamp(s.asof) == frame.timestamp.iloc[i + 1] and pd.Timestamp(s.asof) in stamps


def test_backtest_matches_phase3v_reference(tmp_path):
    result = backtest.run({"name": "orb", "root": "NQ", "interval": "5m", "source": "yahoo", "strategy": {"type": "opening_range_breakout"},
                           "costs": {"slippage_ticks": 1}, "contracts": 2}, tmp_path)
    reference = json.loads((market.ROOT / "reports/phase3v_strategies.json").read_text())["roots"]["NQ"]["strategies"]["opening_range_breakout"]["by_slippage_ticks"]["1.0"]["all"]
    assert (result["summary"]["trades"], result["summary"]["net_pnl"]) == (reference["trades"], reference["net"])
    assert result["summary"]["target_hit_rate"] == pytest.approx(2 / 42, abs=1e-4)  # 2 TP_THEN_TIMEOUT fills


def test_backtest_and_training_reject_bad_configs():
    assert backtest.validate({"root": "XX"})
    assert backtest.validate({"root": "NQ", "interval": "1h", "strategy": {"type": "opening_range_breakout"}})
    assert training.validate({"root": "NQ", "objective": "range_quantile", "model": "logistic"})
    assert training.validate({"root": "NQ", "objective": "direction", "model": "logistic", "last_test_year": 2030})


def test_training_matches_phase3v_reference(tmp_path):
    result = training.run({"root": "NQ", "objective": "range_ge_points", "threshold_points": 350, "model": "logistic",
                           "feature_families": ["price", "volatility"]}, tmp_path)
    reference = json.loads((market.ROOT / "reports/phase3v_research.json").read_text())["roots"]["NQ"]["tasks"]["range_ge_350pts"]["price+volatility_logit"]
    assert result["headline"]["development"] == pytest.approx(reference["development"]["brier_model_minus_baseline"]["mean"], abs=1e-12)
    assert result["headline"]["holdout"] == pytest.approx(reference["holdout"]["brier_model_minus_baseline"]["mean"], abs=1e-12)


def test_session_forecasts_are_append_only_and_idempotent(tmp_path, monkeypatch):
    monkeypatch.setattr(forecasts, "DIR", tmp_path)
    first = forecasts.issue("ES")
    second = forecasts.issue("ES")
    assert first["status"] == "ISSUED" and second["status"] == "ALREADY_ISSUED"
    assert first["forecast_id"] == second["forecast_id"] and first["direction"] is None
    rows = (tmp_path / "forecasts.jsonl").read_text().splitlines()
    assert len(rows) == 1
    before = (tmp_path / "forecasts.jsonl").read_bytes()
    forecasts.evaluate()
    assert (tmp_path / "forecasts.jsonl").read_bytes() == before


def test_job_submission_validates_before_queueing(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "STORE_ROOT", tmp_path)
    monkeypatch.setattr(jobs, "CANCEL", tmp_path / "cancel")
    assert jobs.submit("backtest", {"root": "XX"})["status"] == "REJECTED"
    queued = jobs.submit("backtest", {"name": "t", "root": "ES", "interval": "5m", "strategy": {"type": "vwap_pullback"}, "contracts": 2})
    assert queued["status"] == "QUEUED"
    assert jobs.cancel(queued["job_id"])["status"] == "CANCELLED"
    assert jobs.get(queued["job_id"])["state"] == "DISABLED"
