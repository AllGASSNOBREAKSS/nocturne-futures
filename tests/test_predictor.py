"""Predict engine: probability math, calibration evidence, level map and journal."""
import json

import numpy as np
import pytest

from nocturne.studio import market, predictor

licensed = pytest.mark.skipif(not market.databento_available("NQ"), reason="licensed Databento data is local-only")


def test_exceed_probability_is_monotone_and_bounded():
    grid = np.array([0.1, 0.15, 0.25, 0.4, 0.6, 0.9, 1.1, 1.4])  # quantiles at predictor.QUANTILES
    probs = [predictor.exceed_probability(grid, d)["p"] for d in np.linspace(0.0, 2.0, 81)]
    assert all(0.0 <= p <= 1.0 for p in probs)
    assert all(a >= b - 1e-12 for a, b in zip(probs, probs[1:]))
    assert predictor.exceed_probability(grid, 0.4)["p"] == pytest.approx(0.5)
    assert predictor.exceed_probability(grid, 5.0)["bound"] == "<2.5%"
    assert predictor.exceed_probability(grid, 0.0)["p"] == 1.0


@licensed
def test_prediction_levels_are_consistent_and_calibrated():
    r = predictor.predict("NQ")
    assert r["direction"]["verdict"] == "REJECT" and "No edge" in r["direction"]["message"]
    prices = [l["price"] for l in r["levels"]]
    assert prices == sorted(prices, reverse=True) and len(prices) == len(set(prices))  # merged, ordered
    for side in ("high", "low"):
        q = [r["projected"][side][f"p{int(x * 100)}"] for x in predictor.QUANTILES]
        assert q == sorted(q) if side == "high" else q == sorted(q, reverse=True)
    above = [l for l in r["levels"] if l["side"] == "above" and l["method"] == "excursion distribution"]
    farther = sorted(above, key=lambda l: l["distance_points"])
    assert all(a["touch_probability"] >= b["touch_probability"] - 1e-9 for a, b in zip(farther, farther[1:]))
    cov = r["track_record"]["coverage"]
    for side in ("up", "dn"):
        for key, nominal in (("p10", 0.10), ("p50", 0.50), ("p90", 0.90)):
            assert abs(cov[side][key] - nominal) < 0.03, (side, key, cov[side][key])
    assert r["track_record"]["classifiers"]["touch_prior_high"]["brier"] < r["track_record"]["classifiers"]["touch_prior_high"]["baseline_brier"]
    assert r["trading_decision"] == "NO_TRADE"


@licensed
def test_journal_issues_once_and_never_rewrites(tmp_path, monkeypatch):
    monkeypatch.setattr(predictor, "DIR", tmp_path)  # isolated journal; models retrain into tmp
    first = predictor.predict("ES")
    journal_path = tmp_path / "ES_journal.jsonl"
    before = journal_path.read_bytes()
    second = predictor.predict("ES")
    assert first["journal"]["issued"] == second["journal"]["issued"] == 1
    assert journal_path.read_bytes() == before
    entry = json.loads(before.decode().splitlines()[0])
    assert entry["target_session"] == first["target_session"] and entry["model_version"] == predictor.VERSION
