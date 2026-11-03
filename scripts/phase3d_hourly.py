"""Fixed two-hour research on expanded hourly history, kept apart from sessions."""
import json
from pathlib import Path

import pandas as pd

from nocturne.adapters.history import checksum
from nocturne.research.hourly_dataset import FEATURES, build_hourly_dataset
from phase3d_research import run

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = {"decision": "NO_PROMOTION", "event": "two contiguous future hourly bars",
              "limitations": ["continuous futures proxy: raw contracts and roll mapping unavailable",
                              "last 20% quarantined, never scored; recent dates already examined in Phase 3B",
                              "does not resolve 09:30 boundary or 5-minute stops"], "instruments": {}}
    for instrument in ("NQ", "ES"):
        source = ROOT / f"data/history/yahoo_hourly/{instrument}_60m.csv"
        if not source.exists():
            report["instruments"][instrument] = {"status": "DATA_BLOCKED"}
            continue
        dataset = build_hourly_dataset(pd.read_csv(source), instrument)
        path = ROOT / f"data/research/{instrument}_two_hour_phase3d.csv"
        dataset.to_csv(path, index=False)
        entry = {"rows": len(dataset), "days": dataset.day.nunique(), "source_sha256": checksum(source),
                 "dataset_sha256": checksum(path), "experiments": {}}
        for task in ("direction", "consolidation"):
            for rolling in (None, 120):
                key = task + ("_rolling" if rolling else "_expanding")
                result, predictions = run(dataset, task, rolling, FEATURES, min_train=60,
                                          calibration_groups=20, test_groups=30)
                entry["experiments"][key] = result
                predictions.to_csv(ROOT / f"reports/phase3d_{instrument}_2h_{key}.csv", index=False)
                print(instrument, key, {name: item["metrics"]["brier"] for name, item in result.get("summary", {}).items()})
        report["instruments"][instrument] = entry
    (ROOT / "reports/phase3d_hourly_validation.json").write_text(json.dumps(report, indent=2, default=lambda x: x.item()) + "\n")


if __name__ == "__main__":
    main()
