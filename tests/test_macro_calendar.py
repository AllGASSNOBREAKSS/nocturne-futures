from datetime import datetime, timezone

from nocturne.macro.calendar import (
    CalendarStore,
    EconomicEvent,
    detect_critical_day,
    load_sample_calendar,
)

UTC = timezone.utc


def event(event_id, scheduled, importance="HIGH"):
    return EconomicEvent(
        event_id=event_id,
        name=event_id,
        event_type="TEST",
        scheduled_at=scheduled,
        available_at=scheduled,
        source="test",
        importance=importance,
        instruments=["NQ"],
    )


def test_calendar_store_is_idempotent(tmp_path):
    store = CalendarStore(tmp_path / "events.jsonl")
    item = event("e1", datetime(2026, 11, 3, 14, 30, tzinfo=UTC))
    store.append(item)
    store.append(item)
    assert len(store.all()) == 1
    assert store.upcoming(datetime(2026, 11, 3, 14, 0, tzinfo=UTC))[0].event_id == "e1"


def test_pre_event_lock_and_no_direction(tmp_path):
    store = CalendarStore(tmp_path / "events.jsonl")
    store.append(event("e1", datetime(2026, 11, 3, 14, 30, tzinfo=UTC)))
    state = detect_critical_day(store, datetime(2026, 11, 3, 14, 0, tzinfo=UTC))
    assert state.state == "PRE_EVENT_LOCK"
    assert state.directional_bias is None
    assert state.events


def test_scheduled_high_impact_and_stress(tmp_path):
    store = CalendarStore(tmp_path / "events.jsonl")
    store.append(event("e1", datetime(2026, 11, 4, 13, 0, tzinfo=UTC)))
    scheduled = detect_critical_day(store, datetime(2026, 11, 3, 14, 0, tzinfo=UTC))
    assert scheduled.state == "SCHEDULED_HIGH_IMPACT"
    stressed = detect_critical_day(
        store, datetime(2026, 11, 3, 14, 0, tzinfo=UTC), overnight_gap_atr=2.0
    )
    assert stressed.state == "SCHEDULED_HIGH_IMPACT"
    assert "STRESS_OVERLAY" in stressed.reasons


def test_empty_calendar_is_explicit(tmp_path):
    state = detect_critical_day(CalendarStore(tmp_path / "empty.jsonl"), datetime(2026, 11, 3, tzinfo=UTC))
    assert state.state == "DATA_UNAVAILABLE"
    assert state.directional_bias is None


def test_sample_calendar_is_loaded():
    store = load_sample_calendar()
    upcoming = store.upcoming(datetime(2026, 11, 3, 14, 0, tzinfo=UTC), horizon_hours=24 * 10)
    assert any(item.event_id == "nfp-2026-11-06" for item in upcoming)
    assert all(item.consensus is None for item in upcoming)
