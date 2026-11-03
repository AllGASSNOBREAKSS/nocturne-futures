"""Versioned model registry metadata and optional joblib artifact."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd


@dataclass
class ModelRecord:
    model_id: str
    instrument_id: str
    model_type: str
    version: str
    created_at: str
    feature_columns: list[str]
    train_start: str
    train_end: str
    test_start: str
    test_end: str
    metrics: dict
    dataset_sha256: str
    calibration: str = "platt"
    coefficients: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def dataset_hash(frame: pd.DataFrame) -> str:
    values = pd.util.hash_pandas_object(frame, index=True).values
    return hashlib.sha256(values.tobytes()).hexdigest()


def save_model(
    root: str | Path,
    record: ModelRecord,
    model: object | None = None,
) -> Path:
    directory = Path(root) / record.model_id
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "metadata.json").write_text(
        json.dumps(asdict(record), indent=2) + "\n", encoding="utf-8"
    )
    if model is not None:
        joblib.dump(model, directory / "model.joblib")
    return directory


def load_metadata(root: str | Path, model_id: str) -> dict:
    path = Path(root) / model_id / "metadata.json"
    return json.loads(path.read_text(encoding="utf-8"))


def latest_model_id(root: str | Path) -> str | None:
    directory = Path(root)
    if not directory.exists():
        return None
    candidates = sorted(
        (p for p in directory.iterdir() if (p / "metadata.json").exists()),
        key=lambda p: (p / "metadata.json").stat().st_mtime,
    )
    return candidates[-1].name if candidates else None


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat()
