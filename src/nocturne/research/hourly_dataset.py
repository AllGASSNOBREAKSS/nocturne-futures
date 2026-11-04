"""Two-hour event labels on actual hourly bars, never upsampled to 5 minutes."""
import numpy as np
import pandas as pd

FEATURES = ["momentum_2", "momentum_6", "atr_pct", "realized_vol", "efficiency",
            "range_atr", "hour_sin", "hour_cos", "volume_ratio", "zero_volume_context"]


def build_hourly_dataset(bars, instrument):
    frame = bars.copy().sort_values("timestamp").reset_index(drop=True)
    for column in ("timestamp", "available_at"):
        frame[column] = pd.to_datetime(frame[column], utc=True)
    if frame.timestamp.duplicated().any():
        raise ValueError("duplicate hourly bars")
    previous = frame.close.shift(1)
    tr = pd.concat([frame.high - frame.low, (frame.high - previous).abs(),
                    (frame.low - previous).abs()], axis=1).max(axis=1)
    atr = tr.rolling(24).mean()
    ranges = frame.high.rolling(2).max() - frame.low.rolling(2).min()
    returns = frame.close.pct_change()
    volatility = returns.rolling(24).std()
    path = frame.close.diff().abs().rolling(6).sum()
    volume = frame.volume.rolling(24).mean()
    rows = []
    for i in range(24, len(frame) - 2):
        future = frame.iloc[i + 1:i + 3]
        # Reject closed-market gaps, zero-volume labels and partial/off-grid bars.
        stamps = frame.timestamp.iloc[i:i + 3]
        if not stamps.diff().dropna().eq(pd.Timedelta("1h")).all():
            continue
        if frame.available_at.iloc[i] != future.timestamp.iloc[0] or (future.volume <= 0).any():
            continue
        if not (frame.available_at.iloc[i:i + 3] - stamps).eq(pd.Timedelta("1h")).all():
            continue
        if atr.iloc[i] <= 0 or ranges.iloc[i] <= 0 or volume.iloc[i] <= 0:
            continue
        asof = frame.available_at.iloc[i]
        close = frame.close.iloc[i]
        threshold = .5 * atr.iloc[i] * np.sqrt(2)
        move = future.close.iloc[-1] - close
        current_move = close - frame.close.iloc[i - 2]
        future_range = future.high.max() - future.low.min()
        state = lambda value: "BULL" if value > threshold else "BEAR" if value < -threshold else "NEUTRAL"
        rows.append({"signal_id": f"{instrument}|2h|{asof.isoformat()}", "day": str(asof.date()),
                     "session": "TWO_HOUR_OBSERVED", "feature_available_at": asof,
                     "label_end": future.available_at.iloc[-1], "direction": state(move),
                     "consolidation": int(future_range <= .8 * ranges.iloc[i]),
                     "close": close, "atr_points": atr.iloc[i],
                     "threshold_points": threshold, "move_points": move,
                     "move_atr": move / atr.iloc[i],
                     "persistence_direction": state(current_move),
                     "persistence_consolidation": int(ranges.iloc[i] <= .8 * ranges.iloc[i - 2]),
                     "momentum_2": current_move / atr.iloc[i],
                     "momentum_6": (close - frame.close.iloc[i - 6]) / atr.iloc[i],
                     "atr_pct": atr.iloc[i] / close, "realized_vol": volatility.iloc[i],
                     "efficiency": abs(close - frame.close.iloc[i - 6]) / path.iloc[i] if path.iloc[i] else 0,
                     "range_atr": ranges.iloc[i] / atr.iloc[i],
                     "hour_sin": np.sin(2 * np.pi * asof.hour / 24),
                     "hour_cos": np.cos(2 * np.pi * asof.hour / 24),
                     "volume_ratio": frame.volume.iloc[i] / volume.iloc[i],
                     "zero_volume_context": int((frame.volume.iloc[i - 23:i + 1] == 0).sum()),
                     "future_range": future_range, "future_move": move,
                     "source_limit": "continuous_proxy_contract_and_roll_mapping_unknown"})
    return pd.DataFrame(rows)
