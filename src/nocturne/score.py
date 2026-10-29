"""Score a published call against the official session result."""

from __future__ import annotations

from dataclasses import dataclass

from .models import Call
from .scenarios import bucket_for


@dataclass(frozen=True)
class ScoreRow:
    code: str
    prior_close: float
    predicted_low: float
    predicted_high: float
    predicted_mid: float
    actual_open: float
    actual_high: float
    actual_low: float
    actual_close: float
    close_error: float
    close_error_pct: float
    direction_hit: bool
    band_hit: bool
    range_hit: bool
    range_partial: bool
    r1_break: float
    s1_break: float
    bucket: str


def score_call(call: Call, actual: dict) -> list[ScoreRow]:
    rows: list[ScoreRow] = []
    for code, inst in call.instruments.items():
        a = actual["instruments"][code]
        low, high = call.predicted_close[code]
        mid = (low + high) / 2.0
        range_low, range_high = call.predicted_range[code]
        direction_hit = (mid - inst.prior_close) * (a["close"] - inst.prior_close) > 0
        band_hit = low <= a["close"] <= high
        range_hit = range_low <= a["low"] and a["high"] <= range_high
        range_partial = (
            not range_hit
            and range_low <= a["close"] <= range_high
            and (a["low"] < range_low or a["high"] > range_high)
        )
        level = call.levels[code]
        bucket = bucket_for(call.scenarios, code, a["close"])
        rows.append(
            ScoreRow(
                code=code,
                prior_close=inst.prior_close,
                predicted_low=low,
                predicted_high=high,
                predicted_mid=mid,
                actual_open=a["open"],
                actual_high=a["high"],
                actual_low=a["low"],
                actual_close=a["close"],
                close_error=a["close"] - mid,
                close_error_pct=(a["close"] / mid - 1.0) * 100.0,
                direction_hit=direction_hit,
                band_hit=band_hit,
                range_hit=range_hit,
                range_partial=range_partial,
                r1_break=a["high"] - level.r1,
                s1_break=level.s1 - a["low"],
                bucket=bucket.label if bucket else "outside",
            )
        )
    return rows


def summary(rows: list[ScoreRow]) -> dict[str, float]:
    n = len(rows)
    return {
        "n": n,
        "direction": sum(r.direction_hit for r in rows) / n,
        "band": sum(r.band_hit for r in rows) / n,
        "range_full": sum(r.range_hit for r in rows) / n,
        "range_any": sum(r.range_hit or r.range_partial for r in rows) / n,
        "mean_abs_error_pct": sum(abs(r.close_error_pct) for r in rows) / n,
        "buckets_covered": sum(r.bucket != "outside" for r in rows) / n,
    }
