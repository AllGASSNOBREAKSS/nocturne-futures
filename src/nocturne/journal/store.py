"""Append-only forecast journal and outcome records."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..contracts import Prediction


class Outcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_id: str = Field(min_length=1)
    resolved_at: datetime
    outcome: str = Field(min_length=1)  # TP1 / TP2 / STOP / TIMEOUT / NO_FILL
    exit_price: float | None = None
    points: float | None = None
    notes: str | None = None


class PredictionJournal:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.predictions_path = self.root / "predictions.jsonl"
        self.outcomes_path = self.root / "outcomes.jsonl"

    def _read_predictions(self) -> list[Prediction]:
        if not self.predictions_path.exists():
            return []
        return [
            Prediction.model_validate_json(line)
            for line in self.predictions_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def append(self, prediction: Prediction) -> None:
        if any(p.prediction_id == prediction.prediction_id for p in self._read_predictions()):
            raise ValueError(f"duplicate prediction_id {prediction.prediction_id}")
        with self.predictions_path.open("a", encoding="utf-8") as handle:
            handle.write(prediction.model_dump_json() + "\n")

    def get(self, prediction_id: str) -> Prediction | None:
        for prediction in self._read_predictions():
            if prediction.prediction_id == prediction_id:
                return prediction
        return None

    def latest(self, instrument_id: str) -> Prediction | None:
        matches = [p for p in self._read_predictions() if p.instrument_id == instrument_id]
        if not matches:
            return None
        return max(enumerate(matches), key=lambda item: (item[1].asof_utc, item[0]))[1]

    def all_predictions(self) -> list[Prediction]:
        return self._read_predictions()

    def outcomes(self) -> list[Outcome]:
        if not self.outcomes_path.exists():
            return []
        return [
            Outcome.model_validate_json(line)
            for line in self.outcomes_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def resolve(self, outcome: Outcome) -> None:
        if self.get(outcome.prediction_id) is None:
            raise ValueError(f"unknown prediction {outcome.prediction_id}")
        if any(o.prediction_id == outcome.prediction_id for o in self.outcomes()):
            raise ValueError(f"prediction {outcome.prediction_id} already resolved")
        with self.outcomes_path.open("a", encoding="utf-8") as handle:
            handle.write(outcome.model_dump_json() + "\n")
