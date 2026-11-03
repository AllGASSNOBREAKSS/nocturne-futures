import numpy as np
import pandas as pd

from nocturne.research.hourly_dataset import FEATURES, build_hourly_dataset


def bars():
    stamps = pd.date_range("2025-01-01", periods=100, freq="1h", tz="UTC")
    price = 100 + np.sin(np.arange(100))
    return pd.DataFrame({"timestamp": stamps, "available_at": stamps + pd.Timedelta("1h"),
                         "open": price, "high": price + 1, "low": price - 1, "close": price, "volume": 10})


def test_two_hour_labels_and_features_are_separate():
    frame = bars()
    first = build_hourly_dataset(frame, "NQ")
    changed = frame.copy()
    for col in ("open", "high", "low", "close"):
        changed.loc[30:, col] += 10
    second = build_hourly_dataset(changed, "NQ")
    early = first.feature_available_at <= frame.timestamp.iloc[30]
    pd.testing.assert_frame_equal(first.loc[early, FEATURES], second.loc[early, FEATURES])
    assert (first.label_end - first.feature_available_at).eq(pd.Timedelta("2h")).all()


def test_missing_hour_cannot_be_a_two_hour_label():
    frame = bars().drop(index=50)
    dataset = build_hourly_dataset(frame, "NQ")
    assert (dataset.label_end - dataset.feature_available_at).eq(pd.Timedelta("2h")).all()
