"""Schedule proximity, not price direction. Requires explicit PIT coverage."""
from datetime import timedelta

from .calendar import _utc

EVENT_TYPES = ("FOMC", "CPI", "PPI", "PCE", "NFP", "GDP")


def event_proximity(calendar, asof, coverage=None):
    asof = _utc(asof)
    result = {"asof": asof.isoformat(), "status": "DATA_BLOCKED",
              "reason": "NO_AUTHORIZED_PIT_COVERAGE", "directional_bias": None,
              "trading_decision": "NO_TRADE", "minutes_by_type": {name: None for name in EVENT_TYPES},
              "critical_day": "DATA_UNAVAILABLE", "events": []}
    if not coverage:
        return result
    from datetime import datetime
    try:
        received = _utc(datetime.fromisoformat(coverage["received_at"]))
        start = _utc(datetime.fromisoformat(coverage["coverage_start"]))
        end = _utc(datetime.fromisoformat(coverage["coverage_end"]))
        if (not coverage["license_scope"] or coverage["source"] == "public_schedule_sample"
                or not coverage.get("complete_schedule") or received > asof
                or not start <= asof or end < asof + timedelta(hours=24)):
            return result
        events = calendar.upcoming(asof, 24)
        if any(event.source != coverage["source"] for event in events):
            return result
    except (KeyError, ValueError, TypeError):
        return result
    for event in events:
        if event.event_type in result["minutes_by_type"]:
            delta = (_utc(event.scheduled_at) - asof).total_seconds() / 60
            previous = result["minutes_by_type"][event.event_type]
            result["minutes_by_type"][event.event_type] = delta if previous is None else min(previous, delta)
    high = [event for event in events if event.importance == "HIGH"]
    result.update(status="AVAILABLE", reason=None,
                  critical_day=("PRE_EVENT_LOCK" if any((_utc(e.scheduled_at) - asof).total_seconds() <= 3600 for e in high)
                                else "SCHEDULED_HIGH_IMPACT" if high else "NO_SCHEDULED_HIGH_IMPACT_WITHIN_COVERAGE"),
                  events=[{"event_id": e.event_id, "event_type": e.event_type,
                           "scheduled_at": e.scheduled_at.isoformat(), "source": e.source,
                           "schedule_available_at": e.schedule_available_at.isoformat()}
                          for e in events])
    return result
