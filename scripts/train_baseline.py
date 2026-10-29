#!/usr/bin/env python
"""Walk-forward baseline for next-day direction.

This is deliberately simple: ridge regression on price-derived features, refit
every 21 trading days on an expanding window. It exists to establish a
no-leakage baseline, not to claim an edge. If it cannot beat the always-up
base rate out of sample, it should not be used to size a trade.

Usage:
    python scripts/train_baseline.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocturne.stats import true_range  # noqa: E402

CSV_DIR = ROOT / "data" / "studies" / "daily_15y"
CODES = ("ES", "NQ", "GC", "SI")
MIN_TRAIN = 750  # ~3 years
STEP = 21
RIDGE = 10.0


def features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret1"] = out["close"].pct_change()
    out["ret5"] = out["close"].pct_change(5)
    out["ret20"] = out["close"].pct_change(20)
    out["atr14"] = true_range(out).rolling(14).mean() / out["close"]
    out["sma20_dist"] = out["close"] / out["close"].rolling(20).mean() - 1.0
    out["sma50_dist"] = out["close"] / out["close"].rolling(50).mean() - 1.0
    out["vol20"] = out["ret1"].rolling(20).std() * np.sqrt(252)
    dow = pd.to_datetime(out["date"]).dt.dayofweek
    for day in range(1, 5):
        out[f"dow_{day}"] = (dow == day).astype(float)
    out["target"] = out["ret1"].shift(-1)
    return out


FEATURES = [
    "ret1", "ret5", "ret20", "atr14", "sma20_dist", "sma50_dist", "vol20",
    "dow_1", "dow_2", "dow_3", "dow_4",
]


def walk_forward(df: pd.DataFrame) -> dict[str, float]:
    data = features(df).dropna(subset=FEATURES + ["target"]).reset_index(drop=True)
    X = data[FEATURES].to_numpy(dtype=float)
    y = data["target"].to_numpy(dtype=float)

    predictions = np.full(len(y), np.nan)
    for start in range(MIN_TRAIN, len(y), STEP):
        train = slice(0, start)
        mu = X[train].mean(axis=0)
        sigma = X[train].std(axis=0)
        sigma[sigma == 0] = 1.0
        train_x = np.c_[np.ones(start), (X[train] - mu) / sigma]
        test_x = np.c_[np.ones(min(STEP, len(y) - start)), (X[start:start + STEP] - mu) / sigma]
        gram = train_x.T @ train_x + RIDGE * np.eye(train_x.shape[1])
        weights = np.linalg.solve(gram, train_x.T @ y[train])
        predictions[start:start + STEP] = test_x @ weights

    mask = ~np.isnan(predictions)
    predicted, actual = predictions[mask], y[mask]
    return {
        "n": int(mask.sum()),
        "dir_acc": float(((predicted > 0) == (actual > 0)).mean()),
        "base_up": float((actual > 0).mean()),
        "mae_pct": float(np.abs(predicted - actual).mean() * 100),
        "corr": float(np.corrcoef(predicted, actual)[0, 1]),
        "pred_sd_pct": float(predicted.std() * 100),
        "actual_sd_pct": float(actual.std() * 100),
    }


def main() -> int:
    print(f"{'code':<6}{'n':>7}{'dir acc':>10}{'base up':>10}{'MAE %':>9}{'corr':>8}{'pred sd':>10}")
    for code in CODES:
        path = CSV_DIR / f"{code}.csv"
        if not path.exists():
            raise SystemExit(f"missing {path}; run scripts/run_study.py --fetch first")
        df = pd.read_csv(path)
        result = walk_forward(df)
        print(
            f"{code:<6}{result['n']:>7}{result['dir_acc']:>10.3f}"
            f"{result['base_up']:>10.3f}{result['mae_pct']:>9.3f}"
            f"{result['corr']:>8.3f}{result['pred_sd_pct']:>10.3f}"
        )
    print(
        "\nDirection accuracy must be read against `base up`: predicting every day "
        "up scores the base rate without any model."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
