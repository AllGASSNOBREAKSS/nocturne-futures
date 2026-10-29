"""Descriptive statistics used by the call and the study."""

from __future__ import annotations

import numpy as np
import pandas as pd


def with_returns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["ret"] = out["close"].pct_change() * 100.0
    out["range_pct"] = (out["high"] - out["low"]) / out["close"].shift(1) * 100.0
    return out


def true_range(df: pd.DataFrame) -> pd.Series:
    prev = df["close"].shift(1)
    parts = pd.concat(
        [df["high"] - df["low"], (df["high"] - prev).abs(), (df["low"] - prev).abs()],
        axis=1,
    )
    return parts.max(axis=1)


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    return true_range(df).rolling(n).mean()


def realized_vol(close: pd.Series, n: int = 20) -> float:
    rets = np.log(close / close.shift(1)).dropna().tail(n)
    return float(rets.std(ddof=1) * np.sqrt(252) * 100.0)


def expected_move(price: float, annual_vol_pct: float, z: float = 1.0) -> float:
    return price * (annual_vol_pct / 100.0) / (252 ** 0.5) * z


def summarize(returns: np.ndarray, ranges: np.ndarray) -> dict[str, float]:
    returns = np.asarray(returns, dtype=float)
    ranges = np.asarray(ranges, dtype=float)
    return {
        "n": int(len(returns)),
        "pct_up": round(float((returns > 0).mean() * 100.0), 1),
        "avg_ret": round(float(returns.mean()), 3),
        "median_ret": round(float(np.median(returns)), 3),
        "sd_ret": round(float(returns.std(ddof=1)), 3),
        "avg_range": round(float(ranges.mean()), 3),
        "median_range": round(float(np.median(ranges)), 3),
        "p10": round(float(np.percentile(returns, 10)), 3),
        "p90": round(float(np.percentile(returns, 90)), 3),
    }


def event_stats(df: pd.DataFrame, dates: list[str] | set[str]) -> dict[str, float]:
    data = with_returns(df)
    subset = data[data["date"].isin(set(dates))].dropna(subset=["ret", "range_pct"])
    return summarize(subset["ret"].to_numpy(), subset["range_pct"].to_numpy())


def seasonality(df: pd.DataFrame, month_day: str) -> dict[str, float]:
    data = with_returns(df)
    subset = data[data["date"].str[5:] == month_day].dropna(subset=["ret", "range_pct"])
    return summarize(subset["ret"].to_numpy(), subset["range_pct"].to_numpy())


def all_days(df: pd.DataFrame) -> dict[str, float]:
    data = with_returns(df).dropna(subset=["ret", "range_pct"])
    return summarize(data["ret"].to_numpy(), data["range_pct"].to_numpy())
