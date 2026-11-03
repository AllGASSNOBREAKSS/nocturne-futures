"""Forward-only grouped splits with label-interval purging and time embargo.

Intervals are inclusive: a label ending at a later partition's first feature
time is purged. Embargo is elapsed time before the next partition, not a row
count. The final holdout must be reserved before calling walk_forward.
"""
from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Fold:
    train: pd.DataFrame
    calibration: pd.DataFrame
    test: pd.DataFrame


def checked(frame: pd.DataFrame, group: str = "day") -> pd.DataFrame:
    out = frame.copy()
    for col in ("feature_available_at", "label_end"):
        out[col] = pd.to_datetime(out[col], utc=True, errors="raise")
    if out[[group, "signal_id", "feature_available_at", "label_end"]].isna().any().any():
        raise ValueError("missing validation metadata")
    if (out.label_end < out.feature_available_at).any():
        raise ValueError("label ends before features")
    if out.groupby("signal_id")[group].nunique().gt(1).any():
        raise ValueError("signal spans groups")
    return out.sort_values("feature_available_at").reset_index(drop=True)


def _purge(left, right, group, embargo):
    if left.empty or right.empty:
        return left.copy()
    cutoff = right.feature_available_at.min() - embargo
    eligible = left.groupby(group).label_end.max()
    return left[left[group].isin(eligible[eligible < cutoff].index)].copy()


def reserve_holdout(frame, fraction=0.2, group="day", embargo=pd.Timedelta("1h")):
    if not 0 < fraction < 1 or embargo < pd.Timedelta(0):
        raise ValueError("invalid holdout/embargo")
    frame = checked(frame, group)
    groups = frame.groupby(group).feature_available_at.min().sort_values().index
    split = int(len(groups) * (1 - fraction))
    if split < 1 or split >= len(groups):
        raise ValueError("insufficient groups")
    holdout = frame[frame[group].isin(groups[split:])].copy()
    development = _purge(frame[frame[group].isin(groups[:split])], holdout, group, embargo)
    return development, holdout


def walk_forward(frame, min_train=12, calibration_groups=5, test_groups=5,
                 rolling_groups=None, group="day", embargo=pd.Timedelta("1h")):
    if min(min_train, calibration_groups, test_groups) < 1 or embargo < pd.Timedelta(0):
        raise ValueError("invalid fold configuration")
    if rolling_groups is not None and rolling_groups < min_train:
        raise ValueError("rolling window below minimum training groups")
    frame = checked(frame, group)
    groups = frame.groupby(group).feature_available_at.min().sort_values().index
    folds = []
    for end in range(min_train + calibration_groups, len(groups), test_groups):
        calibration_start = end - calibration_groups
        start = max(0, calibration_start - rolling_groups) if rolling_groups else 0
        train = frame[frame[group].isin(groups[start:calibration_start])]
        calibration = frame[frame[group].isin(groups[calibration_start:end])]
        test = frame[frame[group].isin(groups[end:end + test_groups])]
        calibration = _purge(calibration, test, group, embargo)
        train = _purge(train, frame[frame[group].isin(groups[calibration_start:end])], group, embargo)
        if train.empty or calibration.empty or test.empty:
            continue
        for earlier, later in ((train, calibration), (calibration, test)):
            if earlier.label_end.max() + embargo >= later.feature_available_at.min():
                raise AssertionError("label leakage across fold")
        folds.append(Fold(train.copy(), calibration.copy(), test.copy()))
    return folds


def block_mean_interval(values, groups, block_groups=3, repetitions=1000, seed=7):
    """Moving-block bootstrap of consecutive day groups, keeping rows together.

    Returns a descriptive 95% interval, not a claim of independent samples.
    Input must be in chronological group order.
    """
    data = pd.DataFrame({"value": values, "group": groups})
    if data.empty or not np.isfinite(data.value).all() or block_groups < 1 or repetitions < 1:
        raise ValueError("invalid bootstrap sample")
    chunks = [part.value.to_numpy() for _, part in data.groupby("group", sort=False)]
    n = len(chunks)
    if n < 2:
        return {"mean": float(data.value.mean()), "low": None, "high": None, "groups": n}
    width = min(block_groups, n)
    rng = np.random.default_rng(seed)
    means = []
    for _ in range(repetitions):
        indices = []
        while len(indices) < n:
            start = int(rng.integers(0, n - width + 1))
            indices.extend(range(start, start + width))
        means.append(np.concatenate([chunks[i] for i in indices[:n]]).mean())
    low, high = np.quantile(means, [0.025, 0.975])
    return {"mean": float(data.value.mean()), "low": float(low), "high": float(high),
            "groups": n, "block_groups": width, "repetitions": repetitions}
