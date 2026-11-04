"""Do historical analogues add directional value on decades of daily data?"""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nocturne.adapters.yahoo_history import load_history
from nocturne.research.analogues import FEATURES, analogue_probabilities, build_windows, metrics

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data/history/yahoo_daily"
RESERVED_FROM = "2024-01-01"


def main():
    frame = load_history(DAILY, "^NDX")
    vix = load_history(DAILY, "^VIX").set_index(pd.to_datetime(load_history(DAILY, "^VIX").date)).close
    windows = build_windows(frame, vix=vix)
    columns = [column for column in FEATURES if column in windows.columns]
    report = {"decision": "NO_PROMOTION", "holdout_scored": False,
              "instrument": "^NDX", "label": "next session close-to-close up",
              "features": columns, "k": 100, "embargo_days": 5,
              "reserved_from": RESERVED_FROM,
              "warning": "analogue similarity is descriptive; it does not imply a repeat",
              "variants": {}}
    for k in (50, 100, 250):
        probabilities = analogue_probabilities(windows, columns, start="1995-01-01", k=k,
                                               embargo_days=5, chunk=250)
        probabilities["year"] = pd.to_datetime(probabilities.date).dt.year
        probabilities = probabilities[probabilities.year < 2024]
        joined = windows.merge(probabilities, on="date", how="inner").dropna(subset=["next_up"])
        y = joined.next_up.to_numpy()
        frequency = float(windows[windows.date < pd.Timestamp("1995-01-01")].next_up.mean())
        summary = {"n": len(joined), "k": k,
                   "analogue": metrics(y, joined.analogue_probability),
                   "frequency": metrics(y, np.full(len(joined), frequency)),
                   "first": str(pd.to_datetime(joined.date).min().date()),
                   "last": str(pd.to_datetime(joined.date).max().date()),
                   "mean_neighbour_distance": float(joined.analogue_distance.mean())}
        by_decade = {}
        for decade, group in joined.groupby(joined.year // 10 * 10):
            by_decade[str(int(decade))] = metrics(group.next_up, group.analogue_probability)
        summary["by_decade"] = by_decade
        report["variants"][f"knn_{k}"] = summary
        print(k, summary["analogue"], summary["frequency"])
    (ROOT / "reports/phase3g_analogues.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
