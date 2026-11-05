"""Read-only forecast service used by the API.

The service never places orders. It reads the append-only journal and the model
registry, and returns explicit 404/no-trade states when data is absent.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..contracts import Prediction
from ..journal import PredictionJournal
from ..ml.registry import load_metadata, latest_model_id

ROOT = Path(__file__).resolve().parents[3]


class ForecastService:
    def research_status(self) -> dict:
        path = ROOT / "reports/phase3m_research.json"
        if not path.exists():
            return {"status": "NO_RESEARCH_REPORT", "trading_decision": "NO_TRADE"}
        try:
            report = json.loads(path.read_text())
            stamp = datetime.fromisoformat(report["generated_at"])
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
            return {**report, "snapshot_age_seconds": age,
                    "freshness": "RECENT" if 0 <= age <= 26 * 3600 else "STALE",
                    "view": "read-only timestamped research snapshot; no jobs triggered by HTTP"}
        except (ValueError, KeyError, TypeError):
            return {"status": "INVALID_RESEARCH_REPORT", "trading_decision": "NO_TRADE"}

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
        from ..ml.status import governance
        return {"models": models, "latest": latest_model_id(directory), "governance": governance()}

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

    def forecast_v1(self, instrument_id: str) -> dict:
        path = self.forecast_root / f"{instrument_id.upper()}_v1.json"
        if not path.exists():
            return {"forecast": None, "reason": "NO_V1_FORECAST"}
        return json.loads(path.read_text(encoding="utf-8"))

    def forecast_bundle(self, instrument_id: str) -> dict:
        path = self.forecast_root / f"{instrument_id.upper()}_bundle.json"
        if not path.exists():
            return {"bundle": None, "reason": "NO_BUNDLE_FORECAST"}
        return json.loads(path.read_text(encoding="utf-8"))

    def events_upcoming(self) -> dict:
        path = self.forecast_root / "events.json"
        if not path.exists():
            return {"events": [], "reason": "NO_AUTHORIZED_CALENDAR_ADAPTER"}
        return json.loads(path.read_text(encoding="utf-8"))

    def shadow_status(self) -> dict:
        path = ROOT / "reports" / "phase3h_shadow_status.json"
        if not path.exists():
            return {"status": "NO_SHADOW_RUN", "trading_decision": "NO_TRADE"}
        return json.loads(path.read_text(encoding="utf-8"))

    def shadow_history(self, limit: int = 50) -> dict:
        path = ROOT / "data" / "shadow" / "ndx_range" / "forecasts.jsonl"
        if not path.exists():
            return {"forecasts": [], "reason": "NO_SHADOW_FORECASTS", "trading_decision": "NO_TRADE"}
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return {"count": len(records), "forecasts": records[-limit:][::-1],
                "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW", "trading_decision": "NO_TRADE"}

    def shadow_outcomes(self, limit: int = 50) -> dict:
        path = ROOT / "data/shadow/ndx_range/outcomes.jsonl"
        records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
        return {"count": len(records), "outcomes": records[-limit:][::-1],
                "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW", "trading_decision": "NO_TRADE"}

    def shadow_evaluation(self) -> dict:
        path = ROOT / "reports" / "phase3h_shadow_status.json"
        if not path.exists():
            return {"status": "NO_SHADOW_RUN", "matured": 0, "trading_decision": "NO_TRADE"}
        status = json.loads(path.read_text(encoding="utf-8"))
        return {"model_id": status.get("model_id"), "validation_status": status.get("validation_status"),
                "trading_decision": "NO_TRADE", **status.get("evaluation", {})}

    def shadow_missed(self) -> dict:
        path = ROOT / "data" / "shadow" / "ndx_range" / "missed.jsonl"
        if not path.exists():
            return {"missed": 0, "records": [], "trading_decision": "NO_TRADE", "mode": "read_only_shadow"}
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        return {"missed": len(records), "records": records[-50:], "trading_decision": "NO_TRADE", "mode": "read_only_shadow"}

    def shadow_calibration(self) -> dict:
        path = ROOT / "reports" / "phase3i_forward.json"
        if not path.exists():
            return {"status": "NO_FORWARD_REPORT", "trading_decision": "NO_TRADE"}
        report = json.loads(path.read_text(encoding="utf-8"))
        return {"model_id": report.get("model_id"),
                "generated_at": report.get("generated_at"),
                "validation_status": report.get("validation_status"),
                "issued": report.get("issued"), "matured": report.get("matured"),
                "evaluation": report.get("evaluation"),
                "claim": report.get("claim"),
                "forecast_integrity": report.get("forecast_integrity"),
                "trading_decision": "NO_TRADE"}

    def shadow_verification(self) -> dict:
        path = ROOT / "reports/phase3l_forward_audit.json"
        if not path.exists():
            return {"status": "NO_VERIFICATION_REPORT", "trading_decision": "NO_TRADE"}
        report = json.loads(path.read_text())
        return {**report, "view": "timestamped audit snapshot, not an exchange-finality certification"}

    def futures_readiness(self) -> dict:
        path = ROOT / "reports" / "phase3i_readiness.json"
        result = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "NO_READINESS_REPORT", "trading_decision": "NO_TRADE"}
        access = ROOT / "reports/phase3n_futures_access.json"
        if access.exists():
            try:
                result["acquisition_snapshot"] = json.loads(access.read_text(encoding="utf-8"))
            except ValueError:
                result["acquisition_snapshot"] = {"status": "INVALID_ACCESS_REPORT"}
        return result

    def critical_day_alerts(self) -> dict:
        from ..macro.calendar import CalendarStore
        from ..macro.proximity import event_proximity
        # No authorized schedule manifest is configured. Sample events cannot
        # establish absence of event risk or a directional probability.
        return event_proximity(CalendarStore(), datetime.now(timezone.utc))

    def shadow_operations(self) -> dict:
        from ..shadow import ShadowStore
        from ..shadow.operations import assess_operations
        try:
            status = json.loads((ROOT / "reports/phase3h_shadow_status.json").read_text())
        except (FileNotFoundError, ValueError):
            status = None
        # Assessment only; HTTP GET never appends alert transitions.
        try:
            verification = json.loads((ROOT / "reports/phase3l_forward_audit.json").read_text())
        except (FileNotFoundError, ValueError):
            verification = None
        return assess_operations(ShadowStore(ROOT / "data/shadow/ndx_range"), status,
                                 datetime.now(timezone.utc), outcome_verification=verification)

    def source_revisions(self) -> dict:
        path = ROOT / "data/shadow/market/snapshots/revisions.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
        return {"count": len(rows), "revisions": rows[-50:], "trading_decision": "NO_TRADE",
                "validation_status": "RESEARCH_ONLY", "mode": "read_only_shadow"}

    def source_reconciliations(self) -> dict:
        path = ROOT / "data/shadow/ndx_range/reconciliations.jsonl"
        rows = [json.loads(line) for line in path.read_text().splitlines() if line.strip()] if path.exists() else []
        return {"count": len(rows), "reconciliations": rows[-50:], "trading_decision": "NO_TRADE",
                "validation_status": "RESEARCH_ONLY", "mode": "read_only_shadow"}

    def data_health(self) -> dict:
        status_path = ROOT / "reports" / "phase3h_shadow_status.json"
        coverage_path = ROOT / "reports" / "phase3g_coverage.json"
        result = {"read_only": True, "providers": {}, "sources": {}, "warnings": [],
                  "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW", "trading_decision": "NO_TRADE"}
        if coverage_path.exists():
            coverage = json.loads(coverage_path.read_text(encoding="utf-8"))
            result["sources"] = {name: {"rows": item.get("rows"), "last": item.get("last")}
                                 for name, item in coverage.get("datasets", {}).items()}
        providers_path = ROOT / "reports" / "phase3g_providers.json"
        if providers_path.exists():
            providers = json.loads(providers_path.read_text(encoding="utf-8"))
            result["providers"] = {item["name"]: item["status"] for item in providers.get("providers", [])}
        if status_path.exists():
            status = json.loads(status_path.read_text(encoding="utf-8"))
            result["shadow_last_run"] = status.get("generated_at")
            result["shadow_sources"] = status.get("sources")
            result["quality_failures"] = status.get("evaluation", {}).get("quality_failures")
            if status.get("operational_status") in {"DATA_BLOCKED", "AUDIT_BLOCKED", "CYCLE_FAILED"}:
                result["warnings"].append(status["operational_status"])
            if status.get("generation") not in (None, "STORED", "ALREADY_ISSUED", "EVALUATE_ONLY"):
                result["warnings"].append(f"last shadow generation: {status.get('generation')}")
            age = (datetime.now(timezone.utc) - datetime.fromisoformat(status["generated_at"])).total_seconds()
            result["snapshot_age_seconds"] = age
            if age < 0 or age > 48 * 3600:
                result["warnings"].append("stale or future-dated shadow status")
            from ..shadow import ShadowStore, health
            state = health(ShadowStore(ROOT / "data/shadow/ndx_range"), datetime.now(timezone.utc))
            result["runtime_health"] = state
            result["warnings"].extend(state["warnings"])
        else:
            result["warnings"].append("no shadow run recorded")
        result["status"] = "ok" if not result["warnings"] else "degraded"
        return result

    def health(self) -> dict:
        return {
            "status": "ok",
            "read_only": True,
            "predictions": len(self.journal.all_predictions()),
            "outcomes": len(self.journal.outcomes()),
            "latest_model": latest_model_id(self.registry_root),
        }
