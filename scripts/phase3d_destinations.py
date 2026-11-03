"""Fixed large-target diagnostics on already-examined five-minute history.

Candidates are independent scenarios, not a jointly executable portfolio.
No optimization, promotion, or final-holdout access.
"""
import json
from pathlib import Path

import pandas as pd

from nocturne.backtest.study import build_dataset
from nocturne.research.validation import block_mean_interval
from nocturne.adapters.history import checksum

ROOT = Path(__file__).resolve().parents[1]


def summarize(group):
    known = group[group.target_first.notna()].copy()
    touches = group[group.target_touched.notna()]
    return {"rows": len(group), "signals": group.signal_id.nunique(),
            "first": str(group.feature_available_at.min()), "last": str(group.feature_available_at.max()),
            "outcomes": group.outcome.value_counts().to_dict(),
            "horizon_complete": int(group.horizon_complete.sum()),
            "touch_observed_n": len(touches),
            "touch_rate_observed": float(touches.target_touched.astype(float).mean()) if len(touches) else None,
            "target_first_observed_n": len(known),
            "target_first_observed": block_mean_interval(known.target_first.astype(float), known.day) if len(known) else None,
            "risk_points_median": float((group.entry_price - group.stop_price).abs().median()),
            "target_r_median": float(group.r_multiple.median()),
            "mfe_points_median": float(group.mfe_points.median()),
            "hypothetical_net_mean_observed": float(known.hypothetical_net_dollars.mean()) if len(known) else None,
            "censoring_warning": "observed-outcome rates can be biased by censoring; not calibrated probabilities"}


def main():
    report = {"decision": "NO_PROMOTION", "dataset": "previously_examined_5min_cache",
              "protocol_sha256": checksum(ROOT / "docs/PHASE3D_DESTINATION_PROTOCOL.md"),
              "event": "fixed point targets with original strategy stops; capped at RTH data end",
              "costs": "1 or 3 ticks per side plus $2.50 commission per side; one hypothetical contract",
              "limitations": ["bar-extreme reach, not guaranteed limit-order fill",
                              "same-bar ambiguity is unscored", "no portfolio aggregation",
                              "no probability model trained; rates are retrospective"], "experiments": {}}
    frames = []
    for strategy in ("orb", "vwap", "value"):
        for horizon in (24, 78):
            for slip in (1, 3):
                data, source = build_dataset(strategy, "NQ", horizon_bars=horizon,
                                        target_points=(200, 350, 500), slippage_ticks=slip)
                report["source"] = source
                data["day"] = pd.to_datetime(data.feature_available_at, utc=True).dt.strftime("%Y-%m-%d")
                # Quarantine the latest fifth even though the cache was already examined.
                days = sorted(data.day.unique())
                data = data[data.day.isin(days[:int(.8 * len(days))])].copy()
                key = f"{strategy}_{horizon}bars_{slip}ticks"
                data["experiment"] = key
                frames.append(data)
                report["experiments"][key] = {target: summarize(g.sort_values("feature_available_at"))
                                               for target, g in data.groupby("target_id")}
    pd.concat(frames, ignore_index=True).to_csv(ROOT / "data/research/NQ_destinations_phase3d.csv", index=False)
    report["dataset_sha256"] = checksum(ROOT / "data/research/NQ_destinations_phase3d.csv")
    (ROOT / "reports/phase3d_destinations.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: {t: r["outcomes"] for t, r in targets.items()}
                      for key, targets in report["experiments"].items()}, indent=2))


if __name__ == "__main__":
    main()
