from datetime import datetime, timedelta, timezone

from nocturne.adapters.yahoo import bars_frame, events_from_chart


def payload():
    return {
        "chart": {
            "result": [
                {
                    "meta": {"symbol": "NQ=F"},
                    "timestamp": [1793000100, 1793000400],
                    "indicators": {
                        "quote": [
                            {
                                "open": [28500.0, 28520.0],
                                "high": [28540.0, 28550.0],
                                "low": [28490.0, 28510.0],
                                "close": [28530.0, 28545.0],
                                "volume": [1000, 1200],
                            }
                        ]
                    },
                }
            ]
        }
    }


def test_events_from_chart_maps_instrument_and_quality():
    received = datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc)
    events = events_from_chart(payload(), symbol="NQ=F", interval="5m", received_at=received)
    assert len(events) == 2
    first = events[0]
    assert first.instrument_id == "NQ"
    assert first.event_type.value == "bar"
    assert first.payload["close"] == 28530.0
    assert first.available_at_utc - first.event_time_utc == timedelta(minutes=5)
    assert first.license_scope == "yahoo_public_unofficial"


def test_bars_frame_sorts_and_exposes_columns():
    events = events_from_chart(
        payload(),
        symbol="NQ=F",
        interval="5m",
        received_at=datetime(2026, 11, 3, 15, 0, tzinfo=timezone.utc),
    )
    frame = bars_frame(events)
    assert list(frame.columns) == ["timestamp", "available_at", "open", "high", "low", "close", "volume"]
    assert len(frame) == 2
    assert frame["close"].iloc[-1] == 28545.0
