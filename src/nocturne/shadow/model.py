"""Frozen shadow model artifact loading and prediction."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np

from .features import FeatureSnapshot, FEATURES, feature_matrix


@dataclass(frozen=True)
class ShadowArtifact:
    model_id: str
    version: str
    metadata: dict
    models: dict
    features: tuple[str, ...]

    def predict(self, snapshot: FeatureSnapshot) -> dict:
        if set(snapshot.values) != set(self.features):
            raise ValueError("feature schema mismatch with frozen model")
        matrix = feature_matrix(snapshot)[list(self.features)]
        values = [float(self.models[q].predict(matrix)[0]) for q in ("p50", "p80", "p90")]
        values = np.sort(np.maximum(values, 0.0))
        return {"p50": float(values[0]), "p80": float(values[1]), "p90": float(values[2])}


def load_artifact(root: Path | str, model_id: str) -> ShadowArtifact:
    directory = Path(root) / model_id
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    bundle = joblib.load(directory / "model.joblib")
    features = tuple(bundle["features"])
    if list(features) != list(FEATURES):
        raise ValueError("artifact feature order does not match the frozen schema")
    return ShadowArtifact(model_id=model_id, version=metadata["version"],
                          metadata=metadata, models=bundle["models"], features=features)


def save_artifact(root: Path | str, model_id: str, models: dict, metadata: dict) -> Path:
    directory = Path(root) / model_id
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump({"models": models, "features": list(FEATURES)}, directory / "model.joblib")
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return directory
