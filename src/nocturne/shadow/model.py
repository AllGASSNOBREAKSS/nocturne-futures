"""Frozen shadow model artifact loading and prediction."""
from __future__ import annotations

import json
import hashlib
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
        adjustments = self.metadata["adjustments"]
        values = [float(self.models[q].predict(matrix)[0]) + float(adjustments[q])
                  for q in ("p50", "p80", "p90")]
        if not np.isfinite(values).all():
            raise ValueError("non-finite calibrated quantiles")
        values = np.sort(np.maximum(values, 0.0))
        return {"p50": float(values[0]), "p80": float(values[1]), "p90": float(values[2])}


def load_artifact(root: Path | str, model_id: str) -> ShadowArtifact:
    directory = Path(root) / model_id
    checksums = json.loads((directory / "checksums.json").read_text())
    for filename in ("model.joblib", "metadata.json", "baseline.json"):
        content = (directory / filename).read_bytes()
        # JSON uses canonical semantic bytes so Git CRLF/LF conversion cannot
        # masquerade as a model revision. Pickled weights use exact file bytes.
        if filename.endswith(".json"):
            content = json.dumps(json.loads(content), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
        if hashlib.sha256(content).hexdigest() != checksums[filename]:
            raise ValueError("frozen artifact checksum mismatch")
    metadata = json.loads((directory / "metadata.json").read_text(encoding="utf-8"))
    if (metadata["model_id"] != model_id or metadata["instrument"] != "^NDX"
            or metadata["validation_status"] != "RESEARCH_VALIDATED_PENDING_SHADOW"
            or metadata["trading_decision"] != "NO_TRADE"):
        raise ValueError("artifact identity/governance mismatch")
    baseline_path = directory / "baseline.json"
    if baseline_path.exists():
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        if baseline["dataset_sha256"] != metadata["dataset_sha256"]:
            raise ValueError("baseline dataset mismatch")
        metadata = {**metadata, "baseline_quantiles": baseline["quantiles"]}
    metadata = {**metadata, "artifact_digests": checksums}
    bundle = joblib.load(directory / "model.joblib")
    features = tuple(bundle["features"])
    if list(features) != list(FEATURES):
        raise ValueError("artifact feature order does not match the frozen schema")
    return ShadowArtifact(model_id=model_id, version=metadata["version"],
                          metadata=metadata, models=bundle["models"], features=features)


def save_artifact(root: Path | str, model_id: str, models: dict, metadata: dict) -> Path:
    directory = Path(root) / model_id
    if (directory / "checksums.json").exists():
        raise ValueError("cannot replace a pinned shadow artifact; create a challenger version")
    directory.mkdir(parents=True, exist_ok=True)
    joblib.dump({"models": models, "features": list(FEATURES)}, directory / "model.joblib")
    (directory / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    return directory
