from nocturne.forecast.monitoring import summarize_evaluations


def test_monitoring_excludes_immature_and_separates_instruments_and_horizons():
    rows = [
        {"instrument": "NQ", "horizon": "2h", "outcome": {
            "status": "EVALUATED", "p80_covered": True,
            "target_touches": [{"touch_probability": .7, "touched": True}]}},
        {"instrument": "NQ", "horizon": "2h", "outcome": {
            "status": "NOT_MATURED", "p80_covered": False,
            "target_touches": [{"touch_probability": .7, "touched": False}]}},
        {"instrument": "ES", "horizon": "2h", "outcome": {"status": "DATA_BLOCKED"}},
        {"instrument": "NQ", "horizon": "ASIA", "outcome": {"status": "NOT_MATURED"}},
    ]
    report = summarize_evaluations(rows)
    assert len(report["groups"]) == 3
    nq = next(g for g in report["groups"] if g["instrument"] == "NQ" and g["horizon"] == "2h")
    assert nq["forecasts"] == 2 and nq["matured"] == 1
    assert nq["range_coverage"]["p80"] == {"n": 1, "coverage": 1.0}
    assert abs(nq["touch_brier_descriptive"] - .09) < 1e-9
    assert report["decision"] == "NO_PROMOTION"


def test_monitoring_returns_null_metrics_without_mature_outcomes():
    report = summarize_evaluations([{"outcome": {"status": "NOT_MATURED"}}])
    group = report["groups"][0]
    assert group["touch_brier_descriptive"] is None
    assert group["range_coverage"]["p90"]["coverage"] is None
