"""Read-only forecast service used by the API.

The service never places orders. It reads the append-only journal and the model
registry, and returns explicit 404/no-trade states when data is absent.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..contracts import Prediction
from ..journal import PredictionJournal
from ..ml.registry import load_metadata, latest_model_id

ROOT = Path(__file__).resolve().parents[3]


class ForecastService:
    def __init__(
        self,
        journal_root: str | Path = ROOT / "data" / "journal",
        registry_root: str | Path = ROOT / "models" / "registry",
        forecast_root: str | Path = ROOT / "data" / "forecasts",
    ):
        self.journal = PredictionJournal(journal_root)
        self.registry_root = Path(registry_root)
        self.forecast_root = Path(forecast_root)

    def latest(self, instrument_id: str) -> Prediction | None:
        return self.journal.latest(instrument_id.upper())

    def prediction(self, prediction_id: str) -> Prediction | None:
        return self.journal.get(prediction_id)

    def models_status(self) -> dict:
        directory = self.registry_root
        models = []
        if directory.exists():
            for path in sorted(directory.glob("*/metadata.json")):
                models.append(json.loads(path.read_text(encoding="utf-8")))
        return {"models": models, "latest": latest_model_id(directory)}

    def levels(self, instrument_id: str) -> dict:
        path = self.forecast_root / f"{instrument_id.upper()}_levels.json"
        if not path.exists():
            return {"instrument": instrument_id.upper(), "levels": [], "reason": "NO_LEVEL_ARTIFACT"}
        return json.loads(path.read_text(encoding="utf-8"))

    def auction_profile(self, instrument_id: str, session: str) -> dict:
        path = self.forecast_root / f"{instrument_id.upper()}_{session.upper()}_profile.json"
        if not path.exists():
            return {
                "instrument": instrument_id.upper(),
                "session": session.upper(),
                "profile": None,
                "reason": "DATA_BLOCKED_OR_NOT_BUILT",
            }
        return json.loads(path.read_text(encoding="utf-8"))

    def intermarket_state(self) -> dict:
        path = self.forecast_root / "intermarket.json"
        if not path.exists():
            return {"state": None, "reason": "NOT_BUILT"}
        return json.loads(path.read_text(encoding="utf-8"))

    def premarket_state(self) -> dict:
        path = self.forecast_root / "premarket.json"
        if not path.exists():
            return {"state": None, "reason": "NOT_BUILT"}
        return json.loads(path.read_text(encoding="utf-8"))

    def events_upcoming(self) -> dict:
        path = self.forecast_root / "events.json"
        if not path.exists():
            return {"events": [], "reason": "NO_AUTHORIZED_CALENDAR_ADAPTER"}
        return json.loads(path.read_text(encoding="utf-8"))

    def health(self) -> dict:
        return {
            "status": "ok",
            "read_only": True,
            "predictions": len(self.journal.all_predictions()),
            "outcomes": len(self.journal.outcomes()),
            "latest_model": latest_model_id(self.registry_root),
        }
