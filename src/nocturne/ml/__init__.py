"""Models, calibration and registry."""

from .baseline import FrequencyBaseline, GradientBoostedBaseline, LogisticBaseline
from .calibration import (
    PlattCalibrator,
    brier_score,
    classification_metrics,
    expected_calibration_error,
    log_loss,
    reliability_table,
)
from .registry import ModelRecord, dataset_hash, latest_model_id, load_metadata, save_model

__all__ = [
    "FrequencyBaseline",
    "LogisticBaseline",
    "GradientBoostedBaseline",
    "PlattCalibrator",
    "brier_score",
    "log_loss",
    "classification_metrics",
    "expected_calibration_error",
    "reliability_table",
    "ModelRecord",
    "dataset_hash",
    "save_model",
    "load_metadata",
    "latest_model_id",
]
