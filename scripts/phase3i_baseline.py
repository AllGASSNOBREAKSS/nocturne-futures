"""Freeze a train-only unconditional comparator; never retrain the shadow model."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nocturne.adapters.yahoo_history import load_history
from nocturne.shadow.features import build_history

ROOT = Path(__file__).resolve().parents[1]


def main():
    directory = ROOT / "models/shadow/ndx-range-v1"
    metadata = json.loads((directory / "metadata.json").read_text())
    index = load_history(ROOT / "data/history/yahoo_daily", "^NDX")
    digest = hashlib.sha256(pd.util.hash_pandas_object(
        index[["date", "close", "high", "low", "volume"]], index=False).values.tobytes()).hexdigest()
    if digest != metadata["dataset_sha256"]:
        raise ValueError("frozen research data changed")
    history = build_history(index, load_history(ROOT / "data/history/yahoo_daily", "^VIX"))
    train = history[history.date < pd.Timestamp("2022-01-01") - pd.Timedelta(days=5)].dropna(subset=["next_range_pct"])
    if len(train) != metadata["train_rows"]:
        raise ValueError("training cohort mismatch")
    result = {"dataset_sha256": digest, "train_rows": len(train),
              "train_last": str(train.date.max().date()), "definition": "train-only empirical range quantiles",
              "quantiles": {name: float(np.quantile(train.next_range_pct, q))
                            for name, q in (("p50", .5), ("p80", .8), ("p90", .9))}}
    path = directory / "baseline.json"
    if path.exists():
        if json.loads(path.read_text()) != result:
            raise ValueError("refusing baseline revision")
    else:
        path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
