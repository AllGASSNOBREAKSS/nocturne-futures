"""Build the model training frame from bars, features and barrier labels."""

from __future__ import annotations

import pandas as pd

from .features import FEATURE_COLUMNS, build_daily_features
from .labels import triple_barrier_labels


def build_training_frame(
    bars: pd.DataFrame,
    target_atr: float = 2.0,
    stop_atr: float = 1.0,
    horizon: int = 5,
    ambiguous_policy: str = "AMBIGUOUS",
) -> pd.DataFrame:
    features = build_daily_features(bars)
    labels = triple_barrier_labels(
        bars,
        features["atr14"],
        target_atr=target_atr,
        stop_atr=stop_atr,
        horizon=horizon,
        ambiguous_policy=ambiguous_policy,
    )
    merged = features.iloc[labels["signal_index"].to_numpy()].reset_index(drop=True)
    for column in ("outcome", "entry_index", "entry_price", "target", "stop", "mfe", "mae"):
        merged[column] = labels[column].to_numpy()
    merged["y"] = (merged["outcome"] == "TP_FIRST").astype(int)
    return merged


def binary_sample(frame: pd.DataFrame) -> pd.DataFrame:
    """Rows with a resolved TP/SL outcome only."""
    return frame[frame["outcome"].isin(["TP_FIRST", "SL_FIRST"])].reset_index(drop=True)
