"""Target-first training frame, signal-grouped splits and folds."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from ..ml.target_model import evaluate_folds, evaluate_split
from .intraday_features import build_feature_frame

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_PATHS = (
    ROOT / "data" / "research" / "target_dataset_NQ_vwap.csv",
    ROOT / "data" / "research" / "target_dataset_NQ_orb_diag.csv",
    ROOT / "data" / "research" / "target_dataset_NQ_value.csv",
)

NUMERIC_FEATURES = [
    "time_of_day_min",
    "atr_pct",
    "rv20",
    "or15_size_atr",
    "ib60_size_atr",
    "dist_vwap_atr",
    "dist_poc_atr",
    "dist_vah_atr",
    "dist_val_atr",
    "dist_session_high_atr",
    "dist_session_low_atr",
    "dist_prior_high_atr",
    "dist_prior_low_atr",
    "dist_prior_close_atr",
    "dist_overnight_high_atr",
    "dist_overnight_low_atr",
    "mom5",
    "mom20",
    "trend_strength",
    "range_compression",
    "vol_percentile",
    "es_nq_relative_1h",
    "vix_level",
    "vix_change_5d",
    "risk_atr",
    "target_distance_atr",
    "r_multiple",
    "horizon_bars",
]


def load_targets(paths: tuple[Path, ...] | None = None) -> pd.DataFrame:
    paths = paths or DEFAULT_PATHS
    frames = []
    for path in paths:
        if path.exists():
            frame = pd.read_csv(path)
            frame["source_dataset"] = path.stem
            frames.append(frame)
    if not frames:
        raise FileNotFoundError("no target datasets found")
    return pd.concat(frames, ignore_index=True)


def prepare_binary(frame: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    binary = frame[frame["outcome"].isin(["TP_FIRST", "SL_FIRST"])].copy()
    binary["y"] = (binary["outcome"] == "TP_FIRST").astype(int)
    binary = binary.dropna(
        subset=["atr_pct", "risk_atr", "target_distance_atr", "r_multiple", "horizon_bars"]
    ).reset_index(drop=True)

    dummies = pd.get_dummies(
        binary[["strategy_id", "side"]], prefix=["strategy", "side"], dtype=float
    )
    binary = pd.concat([binary, dummies], axis=1)
    feature_columns = NUMERIC_FEATURES + list(dummies.columns)
    return binary, feature_columns


def split_by_signal(
    frame: pd.DataFrame,
    train_fraction: float = 0.6,
    validation_fraction: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    signals = (
        frame[["signal_id", "signal_asof"]]
        .drop_duplicates()
        .sort_values("signal_asof")
        .reset_index(drop=True)
    )
    n = len(signals)
    train_end = max(1, int(n * train_fraction))
    validation_end = max(train_end + 1, int(n * (train_fraction + validation_fraction)))
    train_ids = set(signals.iloc[:train_end]["signal_id"])
    validation_ids = set(signals.iloc[train_end:validation_end]["signal_id"])
    test_ids = set(signals.iloc[validation_end:]["signal_id"])
    return (
        frame[frame["signal_id"].isin(train_ids)].reset_index(drop=True),
        frame[frame["signal_id"].isin(validation_ids)].reset_index(drop=True),
        frame[frame["signal_id"].isin(test_ids)].reset_index(drop=True),
    )


def expanding_folds(
    frame: pd.DataFrame,
    n_folds: int = 3,
    min_train_fraction: float = 0.5,
    validation_fraction: float = 0.2,
) -> list[tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    signals = (
        frame[["signal_id", "signal_asof"]]
        .drop_duplicates()
        .sort_values("signal_asof")
        .reset_index(drop=True)
    )
    n = len(signals)
    start = max(1, int(n * min_train_fraction))
    fold_size = max(1, (n - start) // n_folds)
    folds = []
    for k in range(n_folds):
        train_end = start + k * fold_size
        test_end = min(n, train_end + fold_size)
        if train_end >= n or test_end <= train_end:
            break
        train_signals = signals.iloc[:train_end]
        validation_count = max(1, int(len(train_signals) * validation_fraction))
        train_ids = set(train_signals.iloc[:-validation_count]["signal_id"])
        validation_ids = set(train_signals.iloc[-validation_count:]["signal_id"])
        test_ids = set(signals.iloc[train_end:test_end]["signal_id"])
        folds.append(
            (
                frame[frame["signal_id"].isin(train_ids)].reset_index(drop=True),
                frame[frame["signal_id"].isin(validation_ids)].reset_index(drop=True),
                frame[frame["signal_id"].isin(test_ids)].reset_index(drop=True),
            )
        )
    return folds


def build_training_frame(
    targets: pd.DataFrame,
    nq_bars: pd.DataFrame,
    es_bars: pd.DataFrame,
    vix_daily: pd.DataFrame,
    spec,
) -> pd.DataFrame:
    return build_feature_frame(targets, nq_bars, es_bars, vix_daily, spec)


__all__ = [
    "DEFAULT_PATHS",
    "NUMERIC_FEATURES",
    "load_targets",
    "prepare_binary",
    "split_by_signal",
    "expanding_folds",
    "build_training_frame",
    "evaluate_split",
    "evaluate_folds",
]
