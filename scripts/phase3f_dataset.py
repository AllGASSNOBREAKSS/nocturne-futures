"""Rebuild additive Phase 3F hourly datasets and verify unchanged labels."""
import json
from pathlib import Path

import pandas as pd

from nocturne.adapters.history import checksum
from nocturne.research.hourly_dataset import build_hourly_dataset

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = {"purpose": "additive diagnostic columns only", "instruments": {}}
    for instrument in ("NQ", "ES"):
        source = ROOT / f"data/history/yahoo_hourly/{instrument}_60m.csv"
        old = pd.read_csv(ROOT / f"data/research/{instrument}_two_hour_phase3d.csv")
        new = build_hourly_dataset(pd.read_csv(source), instrument)
        columns = ["signal_id", "day", "feature_available_at", "label_end", "direction", "consolidation"]
        assert len(new) == len(old), (len(new), len(old))
        compare = new[columns].copy()
        for column in ("feature_available_at", "label_end"):
            compare[column] = compare[column].astype(str)
        pd.testing.assert_frame_equal(compare, old[columns])
        path = ROOT / f"data/research/{instrument}_two_hour_phase3f.csv"
        new.to_csv(path, index=False)
        report["instruments"][instrument] = {"rows": len(new), "labels_unchanged": True,
            "source_sha256": checksum(source), "dataset_sha256": checksum(path),
            "neutral_share": float((new.direction == "NEUTRAL").mean()),
            "added_columns": ["close", "atr_points", "threshold_points", "move_points", "move_atr"]}
        print(instrument, report["instruments"][instrument])
    (ROOT / "reports/phase3f_dataset.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
