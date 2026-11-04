"""Normalized historical analogues for next-session direction research.

Every query uses only windows that ended strictly before the query date minus an
embargo. Features are scale-free so that 1990 and 2020 windows are comparable.
Analogue probabilities are historical neighbour frequencies, never a claim that a
similar chart must repeat.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

FEATURES = ["ret_5", "ret_20", "vol_20", "efficiency_20", "ma_distance", "drawdown_60",
            "volume_z", "range_z"]


def build_windows(frame: pd.DataFrame, vix: pd.Series | None = None) -> pd.DataFrame:
    out = frame.copy()
    out["date"] = pd.to_datetime(out.date)
    out = out.sort_values("date").reset_index(drop=True)
    close = out.close.astype(float)
    returns = close.pct_change()
    volatility = returns.rolling(20).std()
    atr = (out.high - out.low).rolling(20).mean()
    path = close.diff().abs().rolling(20).sum()
    features = pd.DataFrame({
        "date": out.date,
        "ret_5": (close / close.shift(5) - 1) / (volatility * np.sqrt(5)),
        "ret_20": (close / close.shift(20) - 1) / (volatility * np.sqrt(20)),
        "vol_20": volatility / volatility.rolling(250).median(),
        "efficiency_20": (close - close.shift(20)).abs() / path,
        "ma_distance": (close - close.rolling(50).mean()) / (atr * 4),
        "drawdown_60": (close / close.rolling(60).max() - 1) / (atr / close * 4),
        "volume_z": (out.volume - out.volume.rolling(20).mean()) / out.volume.rolling(20).std(),
        "range_z": (out.high - out.low) / atr,
    })
    if vix is not None:
        series = vix.reindex(out.date).ffill()
        features["vix_level"] = series / series.rolling(250).median()
        features["vix_change"] = series.pct_change(5)
    features["next_return"] = close.shift(-1) / close - 1
    features["next_up"] = (features.next_return > 0).astype(float)
    features["next_material"] = (features.next_return.abs() > 0.5 * volatility.shift(-1)).astype(float)
    features.loc[features.next_return.isna(), ["next_up", "next_material"]] = np.nan
    return features.dropna(subset=FEATURES).reset_index(drop=True)


def _standardize(train: np.ndarray, query: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    mean = np.nanmean(train, axis=0)
    std = np.nanstd(train, axis=0)
    std[std == 0] = 1.0
    return (train - mean) / std, (query - mean) / std


def analogue_probabilities(windows: pd.DataFrame, columns: list[str], start: str,
                           k: int = 100, embargo_days: int = 5, chunk: int = 200,
                           target: str = "next_up") -> pd.DataFrame:
    """Expanding historical kNN: query date sees only earlier, embargoed windows."""
    if k < 5 or embargo_days < 1:
        raise ValueError("k and embargo must be positive")
    matrix = windows[columns].to_numpy(dtype=float)
    dates = windows.date.to_numpy()
    outcome = windows[target].to_numpy(dtype=float)
    start_stamp = np.datetime64(pd.Timestamp(start))
    test_indices = np.where(dates >= start_stamp)[0]
    rows = []
    for begin in range(0, len(test_indices), chunk):
        block = test_indices[begin:begin + chunk]
        for index in block:
            cutoff = dates[index] - np.timedelta64(embargo_days, "D")
            history = np.where(dates < cutoff)[0]
            history = history[np.isfinite(outcome[history])]
            if len(history) < 500:
                continue
            train, query = _standardize(matrix[history], matrix[[index]])
            distance = np.sqrt(np.sum((train - query) ** 2, axis=1))
            nearest = np.argpartition(distance, k)[:k]
            weights = 1 / (distance[nearest] + 1e-6)
            probability = float(np.average(outcome[history][nearest], weights=weights))
            rows.append({"date": dates[index], "analogue_probability": probability,
                         "analogue_distance": float(distance[nearest].mean()),
                         "history_n": len(history)})
    return pd.DataFrame(rows)


def metrics(y, p) -> dict:
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    if len(np.unique(y)) < 2:
        return {"n": len(y), "brier": float(np.mean((p - y) ** 2)), "auc": None}
    return {"n": len(y), "brier": float(np.mean((p - y) ** 2)),
            "auc": float(roc_auc_score(y, p)),
            "accuracy": float(np.mean((p >= 0.5) == (y >= 0.5))),
            "base_rate": float(y.mean())}
