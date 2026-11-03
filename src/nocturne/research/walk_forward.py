"""Chronological walk-forward evaluation with a separate calibration slice."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np
import pandas as pd

from ..ml.calibration import PlattCalibrator, classification_metrics
from .features import FEATURE_COLUMNS


@dataclass
class WalkForwardResult:
    predictions: pd.DataFrame
    metrics: dict
    model_name: str
    n_train_min: int


def walk_forward(
    frame: pd.DataFrame,
    model_factory: Callable[[], object],
    model_name: str,
    feature_columns: list[str] | None = None,
    min_train: int = 750,
    step: int = 21,
    calibration_fraction: float = 0.2,
) -> WalkForwardResult:
    feature_columns = feature_columns or FEATURE_COLUMNS
    sample = frame.dropna(subset=feature_columns + ["y"]).reset_index(drop=True)
    sample = sample[sample["outcome"].isin(["TP_FIRST", "SL_FIRST"])].reset_index(drop=True)
    if len(sample) < min_train + step:
        raise ValueError(f"not enough binary samples: {len(sample)}")

    rows = []
    for test_start in range(min_train, len(sample), step):
        train = sample.iloc[:test_start]
        split = int(len(train) * (1 - calibration_fraction))
        fit, calibration = train.iloc[:split], train.iloc[split:]
        if fit["y"].nunique() < 2 or calibration["y"].nunique() < 2:
            continue

        model = model_factory()
        model.fit(fit[feature_columns], fit["y"])
        raw_cal = model.predict_proba(calibration[feature_columns])[:, 1]
        calibrator = PlattCalibrator().fit(raw_cal, calibration["y"].to_numpy())

        test = sample.iloc[test_start : test_start + step]
        if test.empty:
            continue
        raw_test = model.predict_proba(test[feature_columns])[:, 1]
        probabilities = calibrator.predict(raw_test)
        for (_, row), probability in zip(test.iterrows(), probabilities):
            rows.append(
                {
                    "index": int(row["signal_index"]),
                    "date": row["date"],
                    "y": int(row["y"]),
                    "p": float(probability),
                }
            )

    predictions = pd.DataFrame(rows)
    if predictions.empty:
        raise ValueError("walk-forward produced no predictions")
    metrics = classification_metrics(predictions["y"].to_numpy(), predictions["p"].to_numpy())
    return WalkForwardResult(
        predictions=predictions,
        metrics=metrics,
        model_name=model_name,
        n_train_min=min_train,
    )
