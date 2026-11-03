"""Baseline models. Historical frequency first, then logistic and boosted trees."""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


class FrequencyBaseline:
    name = "frequency"

    def __init__(self) -> None:
        self.p_: float = 0.5

    def fit(self, X, y) -> "FrequencyBaseline":
        self.p_ = float(np.mean(y))
        return self

    def predict_proba(self, X) -> np.ndarray:
        p = np.full(len(X), self.p_)
        return np.column_stack([1 - p, p])


class LogisticBaseline:
    name = "logistic"

    def __init__(self, C: float = 0.5, max_iter: int = 1000) -> None:
        self.pipeline = Pipeline(
            [
                ("scaler", StandardScaler()),
                ("clf", LogisticRegression(C=C, max_iter=max_iter, solver="lbfgs")),
            ]
        )

    def fit(self, X, y) -> "LogisticBaseline":
        self.pipeline.fit(X, y)
        return self

    def predict_proba(self, X) -> np.ndarray:
        return self.pipeline.predict_proba(X)

    def coefficients(self, feature_names: list[str]) -> dict[str, float]:
        coefs = self.pipeline.named_steps["clf"].coef_[0]
        return {name: round(float(value), 6) for name, value in zip(feature_names, coefs)}


class GradientBoostedBaseline:
    name = "hist_gradient_boosting"

    def __init__(self, max_iter: int = 200, learning_rate: float = 0.05) -> None:
        self.model = HistGradientBoostingClassifier(
            max_iter=max_iter,
            learning_rate=learning_rate,
            max_depth=3,
            l2_regularization=1.0,
            random_state=7,
        )

    def fit(self, X, y) -> "GradientBoostedBaseline":
        self.model.fit(X, y)
        return self

    def predict_proba(self, X) -> np.ndarray:
        return self.model.predict_proba(X)
