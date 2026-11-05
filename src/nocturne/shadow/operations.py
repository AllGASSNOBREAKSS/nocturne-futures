"""Read-only operational assessment and a separate durable incident journal."""
from datetime import datetime, timedelta, timezone
import hashlib

from .calendar import supported
from .service import health

UTC = timezone.utc


def assess_operations(store, status, now, outcome_verification=None):
    if now.tzinfo is None:
        raise ValueError("timezone-aware monitor time required")
    now = now.astimezone(UTC)
    issues = {}
    if store.outcomes():
        try:
            if outcome_verification is None:
                raise ValueError("no outcome verification report")
            age = (now - datetime.fromisoformat(outcome_verification["generated_at"])).total_seconds()
            if not 0 <= age <= 90 * 60:
                raise ValueError("stale outcome verification")
            expected = outcome_verification["journal_hashes"]
            if (expected["forecasts"] != hashlib.sha256(store.forecast_path.read_bytes()).hexdigest()
                    or expected["outcomes"] != hashlib.sha256(store.outcome_path.read_bytes()).hexdigest()):
                raise ValueError("outcome verification does not bind current journals")
            if (outcome_verification["status"] != "VERIFIED_RESEARCH_GRADE"
                    or outcome_verification.get("verified") != len(store.outcomes())):
                issues["OUTCOME_VERIFICATION_FAILED"] = {"verified": outcome_verification.get("verified")}
        except (KeyError, TypeError, ValueError):
            issues["OUTCOME_VERIFICATION_UNAVAILABLE"] = {}
    if status is not None and (not isinstance(status, dict)
                               or not isinstance(status.get("audit", {}), dict)
                               or not isinstance(status.get("refresh", {}), dict)):
        issues["CYCLE_STATUS_INVALID"] = {}
        status = None
    if not supported(now.date()):
        issues["CALENDAR_OUT_OF_RANGE"] = {}
    if not status:
        issues["NO_CYCLE_STATUS"] = {}
    else:
        try:
            age = (now - datetime.fromisoformat(status["generated_at"])).total_seconds()
            if age < 0 or age > 90 * 60:
                issues["CYCLE_STATUS_STALE"] = {"age_seconds": age}
        except (KeyError, TypeError, ValueError):
            issues["CYCLE_STATUS_INVALID"] = {}
        if status.get("operational_status") in {"DATA_BLOCKED", "AUDIT_BLOCKED", "CYCLE_FAILED"}:
            issues["CYCLE_UNHEALTHY"] = {"operational_status": status["operational_status"],
                                          "reason": status.get("reason")}
        for item in status.get("audit", {}).get("failed", []):
            issues[f"FORECAST_AUDIT:{item['forecast_id']}"] = item
        for symbol, result in status.get("refresh", {}).items():
            if result.get("status") == "FETCH_FAILED":
                issues[f"PROVIDER_REFRESH:{symbol}"] = {"error_type": result.get("error_type")}
    outcomes = {item["forecast_id"] for item in store.outcomes()}
    for missed in store.missed():
        if datetime.fromisoformat(missed["target_date"]).date() >= now.date() - timedelta(days=2):
            issues[f"MISSED_ISSUANCE:{missed['target_date']}"] = {"target_date": missed["target_date"]}
    overdue = []
    for forecast in store.forecasts():
        if forecast["forecast_id"] in outcomes:
            continue
        # This source's documented conservative availability bound, plus an
        # operational grace period. It is not fabricated market finality.
        due = datetime.fromisoformat(forecast["target_date"]).replace(tzinfo=UTC) + timedelta(days=1, hours=6)
        if now >= due:
            item = {"forecast_id": forecast["forecast_id"], "expected_by": due.isoformat()}
            overdue.append(item)
            issues[f"OUTCOME_OVERDUE:{forecast['forecast_id']}"] = item
    cycle_state = (status or {}).get("operational_status")
    invalid = any(key in issues for key in ("CYCLE_STATUS_INVALID", "CYCLE_STATUS_STALE", "NO_CYCLE_STATUS"))
    components = {
        "shadow_cycle": {"status": "DEGRADED" if invalid else "BLOCKED" if cycle_state in {"AUDIT_BLOCKED", "DATA_BLOCKED"} else "FAILED" if cycle_state == "CYCLE_FAILED" else "HEALTHY" if cycle_state == "SHADOW_ACTIVE" else "DEGRADED",
                         "reason": cycle_state or "NO_VALID_CYCLE_STATUS"},
        "forecast_integrity": {"status": "DEGRADED" if invalid else "BLOCKED" if any(key.startswith("FORECAST_AUDIT:") for key in issues) else "HEALTHY",
                               "reason": "see forecast audit issues; reconciliation is evidence-bound, not a health override"},
        "provider_refresh": {"status": "DEGRADED" if invalid else "FAILED" if any(key.startswith("PROVIDER_REFRESH:") for key in issues) else "HEALTHY",
                             "reason": "latest timestamped cycle refresh results; not an uptime guarantee"},
        "outcome_evaluation": {"status": "BLOCKED" if any(key.startswith("OUTCOME_VERIFICATION") for key in issues) else "DEGRADED" if overdue else "HEALTHY",
                               "reason": "pending horizons are expected work, not fabricated outcomes; evaluation requires availability and audit gates"},
    }
    return {"generated_at": now.isoformat(), "status": "degraded" if issues else "ok",
            "components": components,
            "issues": issues, "overdue_outcomes": overdue, "health": health(store, now),
            "issued": len(store.forecasts()), "matured": len(outcomes), "missed": len(store.missed()),
            "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW",
            "trading_decision": "NO_TRADE", "mode": "read_only_shadow",
            "delivery": "local durable alerts only; no external paging configured",
            "limits": "same-host monitoring cannot detect or notify while this host is powered off"}


def monitor_operations(store, status, now, outcome_verification=None):
    report = assess_operations(store, status, now, outcome_verification)
    can_resolve = bool(not {"CYCLE_STATUS_STALE", "CYCLE_STATUS_INVALID", "OUTCOME_VERIFICATION_UNAVAILABLE"}.intersection(report["issues"])
                       and status and status.get("operational_status") == "SHADOW_ACTIVE"
                       and status.get("audit", {}).get("failed") == []
                       )
    report["transitions_now"] = store.sync_alerts(report["issues"], now, resolve_missing=can_resolve)
    latest = {item["key"]: item for item in store.alert_events()}
    report["open_alerts"] = [item for item in latest.values() if item["state"] == "OPEN"]
    if report["open_alerts"]:
        report["status"] = "degraded"
    return report
