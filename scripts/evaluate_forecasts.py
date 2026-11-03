#!/usr/bin/env python
"""Evaluate matured Forecast V1 and bundle journal entries against cached bars."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocturne.backtest.data import load_intraday  # noqa: E402
from nocturne.forecast.bundle import ForecastBundle  # noqa: E402
from nocturne.forecast.evaluation import evaluate_bundle, evaluate_forecast  # noqa: E402
from nocturne.forecast.v1 import ForecastV1  # noqa: E402
from nocturne.forecast.monitoring import summarize_evaluations  # noqa: E402


def _lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    cache, records, v1_results, bundle_results = {}, [], [], []

    def instrument_bars(instrument):
        if instrument not in cache:
            cache[instrument], _ = load_intraday(instrument)
        return cache[instrument]

    for line in _lines(ROOT / "data/journal/forecasts_v1.jsonl"):
        forecast = ForecastV1.model_validate_json(line)
        outcome = evaluate_forecast(forecast, instrument_bars(forecast.instrument), horizon_bars=78).to_dict()
        v1_results.append(outcome)
        records.append({"instrument": forecast.instrument, "horizon": forecast.forecast_horizon,
                        "model_version": forecast.model_version, "regime": forecast.market_regime,
                        "outcome": outcome})
    for line in _lines(ROOT / "data/journal/forecast_bundles.jsonl"):
        bundle = ForecastBundle.model_validate_json(line)
        outcome = evaluate_bundle(bundle, instrument_bars(bundle.instrument))
        bundle_results.append(outcome)
        for session, value in outcome["outcomes"].items():
            outlook = bundle.next_day if session == "NEXT_DAY" else bundle.outlooks[session]
            version = "complete_session_empirical" if "range_status" in outlook.data_provenance else "legacy_unvalidated"
            records.append({"instrument": bundle.instrument, "horizon": session,
                            "model_version": version, "regime": outlook.market_regime,
                            "event_state": outlook.critical_day, "outcome": value})
    report = {
        "instrument": next(iter(cache)) if len(cache) == 1 else "MULTIPLE",
        "instruments": sorted(cache),
        "v1_forecasts": len(v1_results),
        "v1_matured": sum(1 for item in v1_results if item["status"] == "EVALUATED"),
        "v1_not_matured": sum(1 for item in v1_results if item["status"] == "NOT_MATURED"),
        "bundles": len(bundle_results),
        "bundle_outcomes": bundle_results,
        "v1_outcomes": v1_results,
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports/forecast_monitoring.json").write_text(
        json.dumps(summarize_evaluations(records), indent=2) + "\n", encoding="utf-8")
    (ROOT / "reports" / "forecast_evaluation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in ("instrument", "v1_forecasts", "v1_matured", "v1_not_matured", "bundles")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
