from datetime import date, datetime, timezone

import numpy as np
import pandas as pd

from nocturne.backtest.data import add_session_column
from nocturne.instruments import get_instrument
from nocturne.sessions import session_snapshot
from nocturne.research.session_dataset import build_session_dataset

NQ = get_instrument("NQ")


def bars():
    rows = []
    for day in ("2026-11-02", "2026-11-03", "2026-11-04"):
        end = pd.Timestamp(day, tz="UTC") + pd.Timedelta("22h")
        stamps = pd.date_range(end - pd.Timedelta("23h"), end, freq="5min", inclusive="left")
        closes = 100 + np.arange(len(stamps)) * 0.01
        rows.append(pd.DataFrame({"timestamp": stamps, "available_at": stamps + pd.Timedelta("5min"),
                                 "open": closes, "close": closes, "high": closes + .2,
                                 "low": closes - .2, "volume": 10}))
    return add_session_column(pd.concat(rows, ignore_index=True), NQ)


def test_missing_bar_does_not_become_complete_when_clock_passes():
    frame = bars()
    missing = frame.timestamp == pd.Timestamp("2026-11-02 15:00", tz="UTC")
    result = session_snapshot(frame[~missing], NQ, date(2026, 11, 2), "NEW_YORK")
    assert not result.complete


def test_label_timing_and_future_mutation_do_not_change_features():
    frame = bars()
    first = build_session_dataset(frame, frame, pd.DataFrame(), NQ)
    assert len(first) == 6
    assert (pd.to_datetime(first.label_end) > pd.to_datetime(first.feature_available_at)).all()
    altered = frame.copy()
    mask = altered.timestamp >= pd.Timestamp("2026-11-03 00:00", tz="UTC")
    for col in ("open", "high", "low", "close"):
        altered.loc[mask, col] += 50
    second = build_session_dataset(altered, frame, pd.DataFrame(), NQ)
    earlier = first.day == "2026-11-02"
    pd.testing.assert_frame_equal(first.loc[earlier, ["current_return_pct", "efficiency", "current_range_atr"]],
                                  second.loc[earlier, ["current_return_pct", "efficiency", "current_range_atr"]])
    assert not first.loc[earlier, "future_return_pct"].equals(second.loc[earlier, "future_return_pct"])
