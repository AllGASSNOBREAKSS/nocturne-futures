"""Diagnostic parity on the already-used holdout; no fitting or tuning."""
import json
from pathlib import Path

import numpy as np

from nocturne.adapters.yahoo_history import load_history
from nocturne.shadow import load_artifact
from nocturne.shadow.features import FEATURES, FeatureSnapshot, build_history

ROOT = Path(__file__).resolve().parents[1]


def main():
    artifact = load_artifact(ROOT / "models/shadow", "ndx-range-v1")
    history = build_history(load_history(ROOT / "data/history/yahoo_daily", "^NDX"),
                            load_history(ROOT / "data/history/yahoo_daily", "^VIX"))
    holdout = history[history.date >= "2024-01-01"].dropna(subset=["next_range_pct"])
    predictions = []
    for _, row in holdout.iterrows():
        snapshot = FeatureSnapshot(asof="diagnostic", data_date=str(row.date.date()), reference_close=float(row.close),
                                   values={name: float(row[name]) for name in FEATURES},
                                   rows_used=len(history), dataset_sha256="diagnostic")
        predictions.append(list(artifact.predict(snapshot).values()))
    matrix = np.array(predictions)
    actual = holdout.next_range_pct.to_numpy()
    metrics = {}
    for i, (name, q) in enumerate((("p50", .5), ("p80", .8), ("p90", .9))):
        residual = actual - matrix[:, i]
        metrics[name] = {"coverage": float(np.mean(actual <= matrix[:, i])),
                         "pinball_loss": float(np.maximum(q * residual, (q - 1) * residual).mean())}
        for key, value in metrics[name].items():
            if abs(value - artifact.metadata["holdout_reproduced"][name][key]) > 1e-6:
                raise ValueError(f"runtime parity failed: {name}/{key}")
    result = {"status": "PASS", "rows": len(holdout), "metrics": metrics,
              "note": "already-used holdout diagnostic; no new independent evidence or fitting"}
    (ROOT / "reports/phase3i_artifact_audit.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
