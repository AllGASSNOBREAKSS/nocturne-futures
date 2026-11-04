from datetime import datetime, timezone

from nocturne.macro.calendar import CalendarStore, EconomicEvent
from nocturne.macro.proximity import event_proximity

NOW = datetime(2026, 11, 4, 12, tzinfo=timezone.utc)


def manifest():
    return {"received_at": "2026-11-03T00:00:00+00:00", "coverage_start": "2026-11-04T00:00:00+00:00",
            "coverage_end": "2026-11-06T00:00:00+00:00", "license_scope": "test-fixture-only",
            "source": "authorized-fixture", "complete_schedule": True}


def test_missing_coverage_cannot_mean_no_event_risk(tmp_path):
    result = event_proximity(CalendarStore(tmp_path / "events.jsonl"), NOW)
    assert result["status"] == "DATA_BLOCKED"
    assert result["directional_bias"] is None


def test_schedule_proximity_respects_point_in_time(tmp_path):
    store = CalendarStore(tmp_path / "events.jsonl")
    store.append(EconomicEvent(event_id="fixture-cpi", name="fixture", event_type="CPI",
                               scheduled_at="2026-11-04T12:30:00Z", available_at="2026-11-04T12:30:00Z",
                               schedule_available_at="2026-11-03T00:00:00Z", importance="HIGH",
                               source="authorized-fixture", actual=9.9))
    result = event_proximity(store, NOW, manifest())
    assert result["minutes_by_type"]["CPI"] == 30
    assert result["critical_day"] == "PRE_EVENT_LOCK"
    assert "actual" not in result["events"][0]
    assert result["directional_bias"] is None


def test_future_or_partial_coverage_is_blocked(tmp_path):
    store = CalendarStore(tmp_path / "events.jsonl")
    for update in ({"received_at": "2026-11-05T00:00:00Z"}, {"complete_schedule": False},
                   {"coverage_end": "2026-11-04T13:00:00Z"}, {"source": "public_schedule_sample"}):
        assert event_proximity(store, NOW, {**manifest(), **update})["status"] == "DATA_BLOCKED"
