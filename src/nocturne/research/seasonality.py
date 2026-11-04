"""Calendar seasonality with year-block uncertainty and FDR control.

Calendar effects are weak and heavily mined. This module reports effect sizes,
year-block intervals and Benjamini-Hochberg adjusted p-values, and treats a
surviving effect as a hypothesis for out-of-sample testing, not a signal.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["date"] = pd.to_datetime(out.date)
    out = out.sort_values("date").reset_index(drop=True)
    out["return"] = out.close.pct_change()
    out["range_pct"] = (out.high - out.low) / out.close.shift(1)
    out["year"] = out.date.dt.year
    out["month"] = out.date.dt.month
    out["weekday"] = out.date.dt.dayofweek
    out["day_of_month"] = out.date.dt.day
    out["month_day"] = out.date.dt.strftime("%m-%d")
    # Turn of month: last three and first three trading days of each month.
    position = out.groupby([out.date.dt.year, out.date.dt.month]).cumcount()
    size = out.groupby([out.date.dt.year, out.date.dt.month]).date.transform("size")
    out["turn_of_month"] = (position < 3) | (position >= size - 3)
    # Third-Friday expiry week (approximation for standard monthly options).
    out["expiry_week"] = (out.date.dt.day >= 15) & (out.date.dt.day <= 21) & (out.date.dt.dayofweek < 5)
    out["quarter_end_month"] = out.month.isin([3, 6, 9, 12])
    return out.dropna(subset=["return"])


def _year_block_interval(values: pd.Series, years: pd.Series, repetitions: int = 2000, seed: int = 11):
    """Resample whole years, preserving intra-year dependence."""
    grouped = [part.to_numpy() for _, part in values.groupby(years, sort=False)]
    if len(grouped) < 5:
        return None, None
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(repetitions):
        picks = rng.integers(0, len(grouped), len(grouped))
        means.append(np.concatenate([grouped[i] for i in picks]).mean())
    low, high = np.quantile(means, [0.025, 0.975])
    return float(low), float(high)


def _bh(pvalues: list[float]) -> list[float]:
    pvalues = np.asarray(pvalues, dtype=float)
    n = len(pvalues)
    order = np.argsort(pvalues)
    adjusted = np.empty(n)
    running = 1.0
    for rank in range(n - 1, -1, -1):
        index = order[rank]
        running = min(running, pvalues[index] * n / (rank + 1))
        adjusted[index] = min(1.0, running)
    return adjusted.tolist()


def group_statistics(frame: pd.DataFrame, column: str) -> dict:
    rows = []
    for key, group in frame.groupby(column):
        if len(group) < 30:
            continue
        mean = float(group["return"].mean())
        std = float(group["return"].std())
        t_stat = mean / (std / np.sqrt(len(group))) if std > 0 else 0.0
        # Two-sided normal approximation; FDR is applied across all groups later.
        p_value = float(2 * (1 - 0.5 * (1 + math.erf(abs(t_stat) / math.sqrt(2)))))
        low, high = _year_block_interval(group["return"], group["year"])
        rows.append({
            "group": str(key), "n": len(group),
            "mean_return": round(mean, 6), "median_return": round(float(group["return"].median()), 6),
            "up_frequency": round(float((group["return"] > 0).mean()), 4),
            "mean_range_pct": round(float(group["range_pct"].mean()), 6),
            "std_return": round(std, 6), "t_stat": round(float(t_stat), 3), "p_value": p_value,
            "year_block_low": low, "year_block_high": high,
            "years": int(group["year"].nunique()),
        })
    if rows:
        adjusted = _bh([row["p_value"] for row in rows])
        for row, value in zip(rows, adjusted):
            row["p_value_bh"] = round(float(value), 6)
            row["survives_fdr_5pct"] = bool(value <= 0.05)
    return {"groups": rows, "tested": len(rows),
            "survivors": sum(row.get("survives_fdr_5pct", False) for row in rows)}


def summarize(frame: pd.DataFrame) -> dict:
    prepared = prepare(frame)
    effects = {}
    for name, column in (("month", "month"), ("weekday", "weekday"),
                         ("day_of_month", "day_of_month"), ("turn_of_month", "turn_of_month"),
                         ("expiry_week", "expiry_week"), ("quarter_end_month", "quarter_end_month")):
        effects[name] = group_statistics(prepared, column)
    # Same-calendar-date across years is reported descriptively with a high
    # minimum sample, because 30+ years of one date is still one seasonal slice.
    month_day = group_statistics(prepared, "month_day")
    month_day["groups"] = [row for row in month_day["groups"] if row["years"] >= 20]
    month_day["note"] = "descriptive only; overlapping windows and data mining risk"
    return {
        "rows": len(prepared), "first": str(prepared.date.min().date()),
        "last": str(prepared.date.max().date()), "years": int(prepared.year.nunique()),
        "baseline": {"mean_return": float(prepared["return"].mean()),
                     "up_frequency": float((prepared["return"] > 0).mean()),
                     "mean_range_pct": float(prepared["range_pct"].mean())},
        "effects": effects, "month_day": month_day,
        "multiple_testing": "Benjamini-Hochberg within each calendar family",
    }
