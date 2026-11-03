"""Market regime detection and empirical future-regime probabilities.

Current-state detection is rule-based. Future-regime probabilities come from
historical transitions of the same rules, measured only on bars available at
the as-of timestamp. They are research estimates, not validated forecasts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd

from .market_clock import ensure_utc


@dataclass
class RegimeState:
    asof: str
    label: str
    adx: float
    efficiency: float
    overlap: float
    vol_percentile: float
    atr: float
    reasons: list[str] = field(default_factory=list)
    future_probabilities: dict[str, float] | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _atr(frame: pd.DataFrame, window: int = 14) -> pd.Series:
    prev = frame["close"].shift(1)
    tr = pd.concat(
        [frame["high"] - frame["low"], (frame["high"] - prev).abs(), (frame["low"] - prev).abs()],
        axis=1,
    ).max(axis=1)
    return tr.rolling(window).mean()


def _adx(frame: pd.DataFrame, window: int = 14) -> float:
    high, low, close = frame["high"], frame["low"], frame["close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = np.where((up > down) & (up > 0), up, 0.0)
    minus_dm = np.where((down > up) & (down > 0), down, 0.0)
    tr = _atr(frame, window)
    plus_di = 100 * pd.Series(plus_dm, index=frame.index).rolling(window).mean() / tr
    minus_di = 100 * pd.Series(minus_dm, index=frame.index).rolling(window).mean() / tr
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    value = dx.rolling(window).mean().iloc[-1]
    return float(value) if np.isfinite(value) else float("nan")


def _label(frame: pd.DataFrame) -> tuple[str, float, float, float, float, float]:
    atr = _atr(frame)
    current_atr = float(atr.iloc[-1])
    atr_history = atr.dropna().tail(60)
    vol_percentile = float((atr_history <= current_atr).mean()) if len(atr_history) >= 10 else 0.5
    close = frame["close"]
    efficiency = (
        abs(float(close.iloc[-1] - close.iloc[-20]))
        / float(close.diff().abs().tail(20).sum())
        if len(close) >= 21 and close.diff().abs().tail(20).sum() > 0
        else 0.0
    )
    overlap = float(
        ((frame["high"].tail(20).to_numpy() >= frame["low"].shift(1).tail(20).to_numpy())
         & (frame["low"].tail(20).to_numpy() <= frame["high"].shift(1).tail(20).to_numpy())).mean()
    )
    adx = _adx(frame)
    sma20 = float(close.tail(20).mean())
    sma50 = float(close.tail(50).mean()) if len(close) >= 50 else sma20
    trend_up = float(close.iloc[-1]) > sma20 > sma50
    trend_down = float(close.iloc[-1]) < sma20 < sma50

    if vol_percentile >= 0.90 and current_atr > 1.5 * float(np.median(atr_history)):
        label = "STRESS"
    elif vol_percentile >= 0.80:
        label = "EXPANSION"
    elif vol_percentile <= 0.20:
        label = "COMPRESSION"
    elif adx >= 25 and efficiency >= 0.25:
        label = "TREND_UP" if trend_up else "TREND_DOWN" if trend_down else "TRANSITION"
    elif overlap >= 0.60:
        label = "BALANCED"
    else:
        label = "CHOP"
    return label, adx, efficiency, overlap, vol_percentile, current_atr


def classify_regime(
    bars: pd.DataFrame,
    asof: datetime | None = None,
    horizon_bars: int = 24,
    history_bars: int = 1200,
) -> RegimeState:
    frame = bars.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True)
    frame["available_at"] = pd.to_datetime(frame["available_at"], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    if asof is not None:
        frame = frame[frame["available_at"] <= ensure_utc(asof)].reset_index(drop=True)
    if len(frame) < 80:
        raise ValueError("not enough bars for regime")

    label, adx, efficiency, overlap, vol_percentile, atr = _label(frame)
    history = frame.tail(history_bars).reset_index(drop=True)
    labels = []
    for i in range(60, len(history) - horizon_bars):
        try:
            labels.append(_label(history.iloc[: i + 1])[0])
        except ValueError:
            continue
    future = None
    if len(labels) > 30:
        transitions = [labels[i + horizon_bars] for i in range(len(labels) - horizon_bars) if labels[i] == label]
        if len(transitions) >= 10:
            counts = pd.Series(transitions).value_counts(normalize=True)
            future = {str(k): round(float(v), 4) for k, v in counts.items()}

    return RegimeState(
        asof=str(asof or frame["available_at"].iloc[-1]),
        label=label,
        adx=round(adx, 3) if np.isfinite(adx) else 0.0,
        efficiency=round(efficiency, 4),
        overlap=round(overlap, 4),
        vol_percentile=round(vol_percentile, 4),
        atr=round(atr, 4),
        reasons=[
            f"adx={adx:.2f}" if np.isfinite(adx) else "adx=NA",
            f"efficiency={efficiency:.2f}",
            f"overlap={overlap:.2f}",
            f"vol_pct={vol_percentile:.2f}",
        ],
        future_probabilities=future,
    )
