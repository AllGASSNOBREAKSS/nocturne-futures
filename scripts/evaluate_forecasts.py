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


def _lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    bars, _ = load_intraday("NQ")
    v1_results = [
        evaluate_forecast(ForecastV1.model_validate_json(line), bars, horizon_bars=78).to_dict()
        for line in _lines(ROOT / "data" / "journal" / "forecasts_v1.jsonl")
    ]
    bundle_results = [
        evaluate_bundle(ForecastBundle.model_validate_json(line), bars)
        for line in _lines(ROOT / "data" / "journal" / "forecast_bundles.jsonl")
    ]
    report = {
        "instrument": "NQ",
        "v1_forecasts": len(v1_results),
        "v1_matured": sum(1 for item in v1_results if item["status"] == "EVALUATED"),
        "v1_not_matured": sum(1 for item in v1_results if item["status"] == "NOT_MATURED"),
        "bundles": len(bundle_results),
        "bundle_outcomes": bundle_results,
        "v1_outcomes": v1_results,
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "forecast_evaluation.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({key: report[key] for key in ("instrument", "v1_forecasts", "v1_matured", "v1_not_matured", "bundles")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
