"""Session direction models and multiclass metrics.

The direction task is BEAR / NEUTRAL / BULL over the next occurrence of the same
analytical session. Models are chronological and research-only.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

LABELS = (0, 1, 2)
LABEL_NAMES = ("BEAR", "NEUTRAL", "BULL")


@dataclass
class DirectionResult:
    name: str
    metrics: dict
    predictions: pd.DataFrame


def _pipeline(kind: str) -> Pipeline:
    if kind == "logistic":
        return Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median")),
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(C=0.5, max_iter=2000, solver="lbfgs")),
            ]
        )
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            (
                "clf",
                HistGradientBoostingClassifier(
                    max_iter=100,
                    learning_rate=0.05,
                    max_depth=3,
                    l2_regularization=1.0,
                    random_state=7,
                ),
            ),
        ]
    )


def _full_probabilities(calibrator: LogisticRegression, raw: np.ndarray) -> np.ndarray:
    probabilities = calibrator.predict_proba(raw)
    out = np.zeros((len(raw), 3))
    for index, label in enumerate(calibrator.classes_):
        out[:, int(label)] = probabilities[:, index]
    return out


def _align_classes(model, raw: np.ndarray) -> np.ndarray:
    out = np.zeros((len(raw), 3))
    for index, label in enumerate(model.classes_):
        out[:, int(label)] = raw[:, index]
    return out


def _calibrate(raw_validation: np.ndarray, y_validation: np.ndarray, raw_test: np.ndarray) -> np.ndarray:
    if len(np.unique(y_validation)) < 3:
        return raw_test
    calibrator = LogisticRegression(max_iter=1000)
    calibrator.fit(raw_validation, y_validation)
    return _full_probabilities(calibrator, raw_test)


def multiclass_metrics(y: np.ndarray, probabilities: np.ndarray) -> dict:
    y = np.asarray(y, dtype=int)
    probabilities = np.asarray(probabilities, dtype=float)
    predicted = probabilities.argmax(axis=1)
    onehot = np.zeros_like(probabilities)
    onehot[np.arange(len(y)), y] = 1.0
    confidence = probabilities.max(axis=1)
    correct = (predicted == y).astype(float)
    ece = 0.0
    bins = np.linspace(0.0, 1.0, 11)
    for low, high in zip(bins[:-1], bins[1:]):
        upper = confidence <= high if high >= 1.0 else confidence < high
        mask = (confidence >= low) & upper
        if mask.any():
            ece += float(mask.mean()) * abs(float(correct[mask].mean()) - float(confidence[mask].mean()))
    matrix = confusion_matrix(y, predicted, labels=list(LABELS))
    recalls = {}
    for index, name in enumerate(LABEL_NAMES):
        total = int((y == index).sum())
        recalls[name] = round(float(matrix[index, index] / total), 4) if total else None
    return {
        "n": int(len(y)),
        "log_loss": round(float(log_loss(y, probabilities, labels=list(LABELS))), 6),
        "brier": round(float(np.mean(np.sum((probabilities - onehot) ** 2, axis=1))), 6),
        "accuracy": round(float((predicted == y).mean()), 4),
        "ece": round(ece, 6),
        "confusion": matrix.tolist(),
        "per_class_recall": recalls,
    }


def _result(name: str, test: pd.DataFrame, probabilities: np.ndarray) -> DirectionResult:
    predictions = test[["signal_id", "day", "session", "y", "direction"]].copy()
    predictions["p_bear"] = probabilities[:, 0]
    predictions["p_neutral"] = probabilities[:, 1]
    predictions["p_bull"] = probabilities[:, 2]
    predictions["predicted"] = [LABEL_NAMES[index] for index in probabilities.argmax(axis=1)]
    return DirectionResult(name, multiclass_metrics(test["y"].to_numpy(), probabilities), predictions)


def evaluate_direction_split(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
) -> dict[str, DirectionResult]:
    results: dict[str, DirectionResult] = {}

    frequencies = train["y"].value_counts(normalize=True).reindex(list(LABELS), fill_value=0.0).to_numpy()
    frequency_probabilities = np.tile(frequencies, (len(test), 1))
    results["frequency"] = _result("frequency", test, frequency_probabilities)

    for name in ("logistic", "gbm"):
        model = _pipeline(name)
        model.fit(train[feature_columns], train["y"])
        raw_validation = _align_classes(model, model.predict_proba(validation[feature_columns]))
        raw_test = _align_classes(model, model.predict_proba(test[feature_columns]))
        probabilities = _calibrate(raw_validation, validation["y"].to_numpy(), raw_test)
        results[name] = _result(name, test, probabilities)
    return results


__all__ = [
    "LABELS",
    "LABEL_NAMES",
    "DirectionResult",
    "multiclass_metrics",
    "evaluate_direction_split",
]
