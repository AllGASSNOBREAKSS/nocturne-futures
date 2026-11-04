"""Pre-declared equal-weight probability fusion versus standalone models."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nocturne.ml.calibration import classification_metrics
from nocturne.ml.session_model import multiclass_metrics
from nocturne.research.validation import block_mean_interval

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = {"decision": "NO_PROMOTION", "method": "equal-weight average of calibrated probabilities",
              "rationale": "declared before evaluation; no weights fitted, no strategy confluence",
              "instruments": {}}
    for instrument in ("NQ", "ES"):
        frame = pd.read_csv(ROOT / f"reports/phase3f_{instrument}_direction_predictions.csv.gz")
        logistic = frame[frame.model == "logistic"].set_index(["fold", "signal_id"])
        gbm = frame[frame.model == "lightgbm"].set_index(["fold", "signal_id"])
        joined = logistic.join(gbm, lsuffix="_l", rsuffix="_g", how="inner")
        assert len(joined) == len(logistic) == len(gbm)
        y = joined.y_l.to_numpy()
        candidates = {
            "logistic": joined[["p_bear_3_l", "p_neutral_3_l", "p_bull_3_l"]].to_numpy(),
            "lightgbm": joined[["p_bear_3_g", "p_neutral_3_g", "p_bull_3_g"]].to_numpy(),
            "equal_weight_fusion": 0.5 * (joined[["p_bear_3_l", "p_neutral_3_l", "p_bull_3_l"]].to_numpy()
                                          + joined[["p_bear_3_g", "p_neutral_3_g", "p_bull_3_g"]].to_numpy()),
        }
        losses = {name: np.sum((p - np.eye(3)[y]) ** 2, axis=1) for name, p in candidates.items()}
        days = joined["day_l"].to_numpy()
        summary = {}
        for name, p in candidates.items():
            metrics = multiclass_metrics(y, p)
            material = (y != 1).astype(int)
            metrics["material"] = classification_metrics(material, 1 - p[:, 1])
            summary[name] = {"metrics": metrics,
                             "brier_interval": block_mean_interval(losses[name], days),
                             "delta_vs_best_standalone": block_mean_interval(
                                 losses[name] - np.minimum(losses["logistic"], losses["lightgbm"]), days)}
        report["instruments"][instrument] = {"n": len(joined), "summary": summary}
        print(instrument, {k: round(v["metrics"]["brier"], 4) for k, v in summary.items()})
    (ROOT / "reports/phase3f_fusion.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
