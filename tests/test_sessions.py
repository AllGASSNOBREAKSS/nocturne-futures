from datetime import date, datetime, timedelta, timezone

import pandas as pd

from nocturne.instruments import get_instrument
from nocturne.market_clock import to_et
from nocturne.sessions import session_snapshot, session_window_for

UTC = timezone.utc
NQ = get_instrument("NQ")


def bar(ts, close, volume=100):
    return {
        "timestamp": ts,
        "available_at": ts + timedelta(minutes=5),
        "open": close - 0.05,
        "high": close + 0.2,
        "low": close - 0.2,
        "close": close,
        "volume": volume,
    }


def make_bars(start, count, base):
    return [bar(start + timedelta(minutes=5 * i), base + i * 0.1) for i in range(count)]


def frame():
    prior = pd.DataFrame(make_bars(datetime(2026, 10, 30, 13, 30, tzinfo=UTC), 78, 100))
    overnight = pd.DataFrame(make_bars(datetime(2026, 11, 1, 23, 0, tzinfo=UTC), 100, 101))
    rth = pd.DataFrame(make_bars(datetime(2026, 11, 2, 14, 30, tzinfo=UTC), 78, 102))
    return pd.concat([prior, overnight, rth], ignore_index=True)


def test_dst_windows():
    edt = session_window_for(NQ, "NEW_YORK", date(2026, 10, 30))
    est = session_window_for(NQ, "NEW_YORK", date(2026, 11, 2))
    assert edt.start_utc.hour == 13 and edt.start_utc.minute == 30
    assert est.start_utc.hour == 14 and est.start_utc.minute == 30


def test_asia_spans_prior_day():
    window = session_window_for(NQ, "ASIA", date(2026, 11, 2))
    local_start = to_et(window.start_utc)
    assert local_start.date() == date(2026, 11, 1)
    assert local_start.hour == 19
    assert window.end_utc.hour == 8


def test_early_close():
    window = session_window_for(NQ, "NEW_YORK", date(2026, 11, 27))
    assert window.end_utc.hour == 18 and window.end_utc.minute == 0


def test_snapshot_fields_and_completion():
    snapshot = session_snapshot(
        frame(), NQ, date(2026, 11, 2), "NEW_YORK", datetime(2026, 11, 2, 21, 0, tzinfo=UTC)
    )
    assert snapshot is not None
    assert snapshot.complete is True
    assert snapshot.bars == 78
    assert snapshot.high > snapshot.low
    assert snapshot.vwap is not None
    assert snapshot.prior_high is not None
    assert snapshot.ib_high is not None
    assert snapshot.profile_method == "BAR_APPROXIMATION"

    partial = session_snapshot(
        frame(), NQ, date(2026, 11, 2), "NEW_YORK", datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    )
    assert partial is not None
    assert partial.complete is False
    assert partial.bars == 18


def test_snapshot_does_not_use_future_bars():
    bars = frame()
    asof = datetime(2026, 11, 2, 16, 0, tzinfo=UTC)
    first = session_snapshot(bars, NQ, date(2026, 11, 2), "NEW_YORK", asof)
    future = pd.DataFrame(make_bars(datetime(2026, 11, 2, 17, 0, tzinfo=UTC), 20, 200))
    second = session_snapshot(
        pd.concat([bars, future], ignore_index=True), NQ, date(2026, 11, 2), "NEW_YORK", asof
    )
    assert first is not None and second is not None
    assert first.to_dict() == second.to_dict()
