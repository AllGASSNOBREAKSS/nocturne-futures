"""Rebuild v2 barrier datasets; report event counts, not pseudo-trading profits."""
import json
from pathlib import Path

from nocturne.backtest.study import build_dataset
from nocturne.adapters.history import checksum

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = {"status": "RESEARCH_ONLY", "promotion": "NO_PROMOTION", "datasets": {}}
    for strategy in ("orb", "vwap", "value"):
        data, meta = build_dataset(strategy, "NQ")
        path = ROOT / f"data/research/target_dataset_NQ_{strategy}_phase3d.csv"
        data.to_csv(path, index=False)
        resolved = data[data.outcome.isin(["TP_FIRST", "SL_FIRST", "TIMEOUT"])]
        report["datasets"][strategy] = {
            "rows": len(data), "signals": data.signal_id.nunique(),
            "outcomes": data.outcome.value_counts().to_dict(),
            "event": "TP_FIRST before SL within exactly 24 observed 5-minute bars",
            "timeouts": "no target-first event, not a realized stop loss",
            "censoring": "incomplete horizon or internal data gap; excluded from binary event rate",
            "event_rate": float(resolved.target_first.astype(float).mean()) if len(resolved) else None,
            "risk_points_median": float((data.entry_price - data.stop_price).abs().median()),
            "target_distance_points_median": float((data.target_price - data.entry_price).abs().median()),
            "source": meta, "sha256": checksum(path),
            "cost_evaluation": "Use existing event-driven backtester. Correlated target rows are not independent trades.",
            "time_to_target": "bars_to_target is zero-based from entry bar; intrabar time unknown"}
    (ROOT / "reports/phase3d_target_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v["outcomes"] for k, v in report["datasets"].items()}, indent=2))


if __name__ == "__main__":
    main()
