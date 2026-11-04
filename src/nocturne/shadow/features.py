"""Point-in-time daily features for the validated NDX range model.

Feature definitions are frozen: changing them creates a new model version. Only
bars with ``available_at <= asof`` are used, and the daily adapter marks a bar
available at the next UTC midnight after its session.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

import numpy as np
import pandas as pd

FEATURES = ["ret_1_abs", "ret_5_abs", "vol_20", "vol_ratio", "atr_pct", "range_atr",
            "efficiency_20", "volume_z", "vix_level", "vix_change_5", "weekday"]
MIN_HISTORY = 260


@dataclass(frozen=True)
class FeatureSnapshot:
    asof: str
    data_date: str
    reference_close: float
    values: dict
    rows_used: int
    dataset_sha256: str

    def digest(self) -> str:
        payload = f"{self.data_date}|{self.reference_close}|{self.values}|{self.dataset_sha256}"
        return hashlib.sha256(payload.encode()).hexdigest()


def _prepare(frame: pd.DataFrame, asof: pd.Timestamp | None) -> pd.DataFrame:
    out = frame.copy()
    for column in ("date", "close", "open", "high", "low", "volume"):
        if column not in out:
            raise ValueError(f"missing required column: {column}")
    out["date"] = pd.to_datetime(out.date)
    if "available_at" in out:
        out["available_at"] = pd.to_datetime(out.available_at, utc=True)
        if asof is not None:
            out = out[out.available_at <= asof]
    return out.sort_values("date").reset_index(drop=True)


def _feature_frame(index: pd.DataFrame, vix: pd.DataFrame) -> pd.DataFrame:
    close = index.close.astype(float)
    high, low = index.high.astype(float), index.low.astype(float)
    returns = close.pct_change()
    volatility = returns.rolling(20).std()
    true_range = pd.concat([high - low, (high - close.shift(1)).abs(),
                            (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr = true_range.rolling(20).mean()
    data = pd.DataFrame({
        "date": index.date,
        "close": close,
        "atr": atr,
        "ret_1_abs": returns.abs() / volatility,
        "ret_5_abs": (close / close.shift(5) - 1).abs() / (volatility * np.sqrt(5)),
        "vol_20": volatility / volatility.rolling(250).median(),
        "vol_ratio": volatility / volatility.rolling(250).mean(),
        "atr_pct": atr / close,
        "range_atr": (high - low) / atr,
        "efficiency_20": (close - close.shift(20)).abs() / close.diff().abs().rolling(20).sum(),
        "weekday": index.date.dt.dayofweek,
    })
    volume_mean = index.volume.rolling(20).mean()
    volume_std = index.volume.rolling(20).std()
    volume_z = (index.volume - volume_mean) / volume_std
    data["volume_z"] = volume_z.mask(volume_std.eq(0), 0.0)
    series = vix.set_index("date").close
    series.index = pd.to_datetime(series.index)
    aligned = series.reindex(data.date).ffill().set_axis(data.index)
    data["vix_level"] = aligned / aligned.rolling(250).median()
    data["vix_change_5"] = aligned.pct_change(5)
    return data


def build_history(index_bars: pd.DataFrame, vix_bars: pd.DataFrame) -> pd.DataFrame:
    """Full labelled history for training. Labels use the next session."""
    index = _prepare(index_bars, None)
    vix = _prepare(vix_bars, None)
    data = _feature_frame(index, vix)
    high, low = index.high.astype(float), index.low.astype(float)
    data["next_range_pct"] = (high.shift(-1) - low.shift(-1)) / data.close
    return data


def build_features(index_bars: pd.DataFrame, vix_bars: pd.DataFrame,
                   asof: pd.Timestamp) -> FeatureSnapshot:
    """Compute the frozen feature row using data available at ``asof``."""
    asof = pd.Timestamp(asof)
    if asof.tzinfo is None:
        raise ValueError("timezone-aware asof required")
    index = _prepare(index_bars, asof)
    vix = _prepare(vix_bars, asof)
    if len(index) < MIN_HISTORY:
        raise ValueError(f"insufficient history: {len(index)} < {MIN_HISTORY}")
    data = _feature_frame(index, vix)
    latest = data.iloc[-1]
    values = {name: float(latest[name]) for name in FEATURES}
    if any(not np.isfinite(value) for value in values.values()):
        missing = [name for name, value in values.items() if not np.isfinite(value)]
        raise ValueError(f"non-finite features: {missing}")
    if values["vix_level"] <= 0:
        raise ValueError("invalid VIX level")
    digest_source = index.tail(MIN_HISTORY)[["date", "close", "high", "low", "volume"]].to_csv(index=False, lineterminator="\n")
    return FeatureSnapshot(
        asof=asof.isoformat(), data_date=str(latest.date.date()),
        reference_close=float(latest.close), values=values, rows_used=len(index),
        dataset_sha256=hashlib.sha256(digest_source.encode()).hexdigest())


def feature_matrix(snapshot: FeatureSnapshot) -> pd.DataFrame:
    return pd.DataFrame([snapshot.values])[FEATURES]
