import json

import pandas as pd

from nocturne.ml.registry import (
    ModelRecord,
    dataset_hash,
    latest_model_id,
    load_metadata,
    save_model,
    now_utc,
)


def test_registry_roundtrip(tmp_path):
    frame = pd.DataFrame({"x": [1, 2, 3], "y": [0, 1, 0]})
    record = ModelRecord(
        model_id="nq-logistic-2026-11-03",
        instrument_id="NQ",
        model_type="logistic",
        version="0.1.0",
        created_at=now_utc(),
        feature_columns=["ret1"],
        train_start="2020-01-01",
        train_end="2024-01-01",
        test_start="2024-01-02",
        test_end="2025-01-01",
        metrics={"brier": 0.2},
        dataset_sha256=dataset_hash(frame),
    )
    save_model(tmp_path, record)
    assert latest_model_id(tmp_path) == record.model_id
    loaded = load_metadata(tmp_path, record.model_id)
    assert loaded["instrument_id"] == "NQ"
    assert loaded["metrics"]["brier"] == 0.2
