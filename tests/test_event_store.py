from datetime import date, datetime, timedelta, timezone

from nocturne.contracts import EventType, MarketEvent, Quality
from nocturne.storage import EventStore

UTC = timezone.utc


def make_event(event_id: str, minute: int, available_minute: int | None = None) -> MarketEvent:
    start = datetime(2026, 11, 3, 14, 30, tzinfo=UTC) + timedelta(minutes=minute)
    available = datetime(2026, 11, 3, 14, 30, tzinfo=UTC) + timedelta(
        minutes=available_minute if available_minute is not None else minute
    )
    return MarketEvent(
        event_id=event_id,
        source="test",
        instrument_id="NQ",
        event_type=EventType.BAR,
        event_time_utc=start,
        available_at_utc=available,
        received_at_utc=available + timedelta(seconds=1),
        source_sequence=minute,
        payload={"close": 100.0 + minute},
        quality=Quality(coverage=1.0),
    )


def test_append_and_read_roundtrip(tmp_path):
    store = EventStore(tmp_path)
    event = make_event("a", 0)
    store.append(event)
    assert store.count("NQ") == 1
    assert list(store.read("NQ"))[0].event_id == "a"


def test_replay_filters_on_available_at(tmp_path):
    store = EventStore(tmp_path)
    store.append(make_event("a", 0, available_minute=5))
    store.append(make_event("b", 1, available_minute=10))

    asof = datetime(2026, 11, 3, 14, 36, tzinfo=UTC)
    replayed = store.replay("NQ", asof)
    assert [event.event_id for event in replayed] == ["a"]


def test_replay_sorts_out_of_order_writes(tmp_path):
    store = EventStore(tmp_path)
    store.append(make_event("late", 5, available_minute=5))
    store.append(make_event("early", 1, available_minute=1))

    replayed = store.replay("NQ", datetime(2026, 11, 3, 15, 0, tzinfo=UTC))
    assert [event.event_id for event in replayed] == ["early", "late"]


def test_dedupe_append_many(tmp_path):
    store = EventStore(tmp_path)
    events = [make_event("a", 0), make_event("a", 0), make_event("b", 1)]
    written = store.append_many(events)
    assert written == 2
    assert store.count("NQ") == 2


def test_watermark_is_latest_available(tmp_path):
    store = EventStore(tmp_path)
    store.append(make_event("a", 0, available_minute=5))
    store.append(make_event("b", 1, available_minute=10))
    assert store.watermark("NQ") == datetime(2026, 11, 3, 14, 40, tzinfo=UTC)


def test_partition_by_utc_date(tmp_path):
    store = EventStore(tmp_path)
    store.append(make_event("a", 0))
    next_day = make_event("b", 0).model_copy(
        update={
            "event_time_utc": datetime(2026, 11, 4, 14, 30, tzinfo=UTC),
            "available_at_utc": datetime(2026, 11, 4, 14, 30, tzinfo=UTC),
            "received_at_utc": datetime(2026, 11, 4, 14, 30, tzinfo=UTC),
        }
    )
    store.append(next_day)
    files = sorted(path.name for path in (tmp_path / "NQ").glob("*.jsonl"))
    assert files == ["2026-11-03.jsonl", "2026-11-04.jsonl"]
