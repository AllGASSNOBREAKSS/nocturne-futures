import numpy as np
import pandas as pd
import pytest

from nocturne.ml.calibration import (
    brier_score,
    classification_metrics,
    expected_calibration_error,
    log_loss,
)
from nocturne.ml.baseline import LogisticBaseline
from nocturne.research.dataset import build_training_frame
from nocturne.research.walk_forward import walk_forward


def make_bars(n=1200):
    rng = np.random.default_rng(7)
    close = 100 * np.exp(np.cumsum(rng.normal(0, 0.012, n)))
    open_ = close * (1 + rng.normal(0, 0.002, n))
    high = np.maximum(open_, close) * (1 + abs(rng.normal(0, 0.006, n)))
    low = np.minimum(open_, close) * (1 - abs(rng.normal(0, 0.006, n)))
    return pd.DataFrame(
        {
            "date": pd.date_range("2020-01-01", periods=n, freq="B").strftime("%Y-%m-%d"),
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
        }
    )


def test_perfect_calibration_scores():
    y = np.array([0, 1, 0, 1])
    p = np.array([0.0, 1.0, 0.0, 1.0])
    assert brier_score(y, p) == pytest.approx(0.0)
    assert expected_calibration_error(y, p) == pytest.approx(0.0)
    assert log_loss(y, p) < 1e-6


def test_walk_forward_produces_predictions():
    frame = build_training_frame(make_bars(), target_atr=1.5, stop_atr=1.0, horizon=5)
    result = walk_forward(
        frame,
        model_factory=LogisticBaseline,
        model_name="logistic",
        min_train=400,
        step=100,
    )
    assert len(result.predictions) > 0
    assert result.predictions["p"].between(0, 1).all()
    assert result.metrics["n"] == len(result.predictions)
    assert "brier" in result.metrics
    assert result.metrics["base_rate"] >= 0


def test_classification_metrics_shape():
    metrics = classification_metrics(np.array([0, 1, 1, 0]), np.array([0.2, 0.8, 0.6, 0.4]))
    assert set(["n", "base_rate", "brier", "log_loss", "accuracy", "ece", "reliability"]) <= set(metrics)
