"""Target-first probability models with chronological calibration."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .baseline import FrequencyBaseline
from .calibration import PlattCalibrator, classification_metrics


@dataclass
class TargetModelResult:
    name: str
    metrics: dict
    predictions: pd.DataFrame
    coefficients: dict[str, float] = field(default_factory=dict)


def _logistic() -> Pipeline:
    return Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(C=0.5, max_iter=1000, solver="lbfgs")),
        ]
    )


def _gbm() -> Pipeline:
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


def _evaluate(
    name: str,
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
    model_factory=None,
) -> TargetModelResult:
    if model_factory is None:
        frequency = FrequencyBaseline().fit(train[feature_columns], train["y"])
        probability = frequency.predict_proba(test[feature_columns])[:, 1]
        meta_columns = [c for c in ["signal_id", "y", "outcome", "strategy_id", "r_multiple"] if c in test.columns]
        predictions = test[meta_columns].copy()
        predictions["p"] = probability
        metrics = classification_metrics(test["y"].to_numpy(), probability)
        if test["y"].nunique() == 2:
            metrics["auc"] = round(float(roc_auc_score(test["y"], probability)), 4)
        return TargetModelResult(name, metrics, predictions)

    model = model_factory()
    model.fit(train[feature_columns], train["y"])
    if validation["y"].nunique() < 2:
        probability = model.predict_proba(test[feature_columns])[:, 1]
    else:
        raw_validation = model.predict_proba(validation[feature_columns])[:, 1]
        calibrator = PlattCalibrator().fit(raw_validation, validation["y"].to_numpy())
        probability = calibrator.predict(model.predict_proba(test[feature_columns])[:, 1])
    meta_columns = [c for c in ["signal_id", "y", "outcome", "strategy_id", "r_multiple"] if c in test.columns]
    predictions = test[meta_columns].copy()
    predictions["p"] = probability
    metrics = classification_metrics(test["y"].to_numpy(), probability)
    metrics["uncalibrated"] = classification_metrics(test.y.to_numpy(), model.predict_proba(test[feature_columns])[:, 1])
    metrics["calibration_status"] = "time_separated_platt" if validation.y.nunique() == 2 else "unavailable_missing_classes"
    if test["y"].nunique() == 2:
        metrics["auc"] = round(float(roc_auc_score(test["y"], probability)), 4)
    coefficients = {}
    if name == "logistic":
        coefficients = {
            feature: round(float(value), 6)
            for feature, value in zip(
                feature_columns, model.named_steps["clf"].coef_[0]
            )
        }
    return TargetModelResult(name, metrics, predictions, coefficients)


def evaluate_split(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    feature_columns: list[str],
) -> dict[str, TargetModelResult]:
    return {
        "frequency": _evaluate("frequency", train, validation, test, feature_columns, None),
        "logistic": _evaluate("logistic", train, validation, test, feature_columns, _logistic),
        "gbm": _evaluate("gbm", train, validation, test, feature_columns, _gbm),
    }


def evaluate_folds(
    folds: list[tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]],
    feature_columns: list[str],
) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for index, (train, validation, test) in enumerate(folds):
        if train["y"].nunique() < 2 or validation["y"].nunique() < 2:
            continue
        results = evaluate_split(train, validation, test, feature_columns)
        for name, result in results.items():
            entry = summary.setdefault(name, {"folds": [], "brier": [], "log_loss": [], "accuracy": []})
            entry["folds"].append(index)
            entry["brier"].append(result.metrics["brier"])
            entry["log_loss"].append(result.metrics["log_loss"])
            entry["accuracy"].append(result.metrics["accuracy"])
    for name, entry in summary.items():
        entry["mean_brier"] = round(float(np.mean(entry["brier"])), 6)
        entry["mean_log_loss"] = round(float(np.mean(entry["log_loss"])), 6)
        entry["mean_accuracy"] = round(float(np.mean(entry["accuracy"])), 4)
    return summary
