"""Calibration metrics and a Platt calibrator."""

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression


class PlattCalibrator:
    def __init__(self) -> None:
        self.model: LogisticRegression | None = None

    def fit(self, scores: np.ndarray, y: np.ndarray) -> "PlattCalibrator":
        self.model = LogisticRegression(C=1e6, solver="lbfgs", max_iter=1000)
        self.model.fit(np.asarray(scores).reshape(-1, 1), np.asarray(y))
        return self

    def predict(self, scores: np.ndarray) -> np.ndarray:
        if self.model is None:
            raise RuntimeError("calibrator is not fitted")
        return self.model.predict_proba(np.asarray(scores).reshape(-1, 1))[:, 1]


def brier_score(y: np.ndarray, p: np.ndarray) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean((p - y) ** 2))


def log_loss(y: np.ndarray, p: np.ndarray, eps: float = 1e-12) -> float:
    y = np.asarray(y, dtype=float)
    p = np.clip(np.asarray(p, dtype=float), eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def accuracy(y: np.ndarray, p: np.ndarray, threshold: float = 0.5) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    return float(np.mean((p >= threshold) == (y >= 0.5)))


def expected_calibration_error(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1.0 else p <= hi)
        if not mask.any():
            continue
        total += mask.mean() * abs(p[mask].mean() - y[mask].mean())
    return float(total)


def reliability_table(y: np.ndarray, p: np.ndarray, bins: int = 10) -> list[dict]:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    edges = np.linspace(0.0, 1.0, bins + 1)
    rows = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (p >= lo) & (p < hi if hi < 1.0 else p <= hi)
        if not mask.any():
            continue
        rows.append(
            {
                "bin_low": round(float(lo), 2),
                "bin_high": round(float(hi), 2),
                "n": int(mask.sum()),
                "mean_predicted": round(float(p[mask].mean()), 4),
                "observed_rate": round(float(y[mask].mean()), 4),
            }
        )
    return rows


def classification_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    y = np.asarray(y, dtype=float)
    p = np.asarray(p, dtype=float)
    predicted = p >= 0.5
    tp = float(((predicted == 1) & (y == 1)).sum())
    precision = tp / float(predicted.sum()) if predicted.sum() else 0.0
    recall = tp / float((y == 1).sum()) if (y == 1).sum() else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "n": int(len(y)),
        "base_rate": round(float(np.mean(y)), 4),
        "brier": round(brier_score(y, p), 6),
        "log_loss": round(log_loss(y, p), 6),
        "accuracy": round(accuracy(y, p), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "ece": round(expected_calibration_error(y, p), 6),
        "reliability": reliability_table(y, p),
    }
