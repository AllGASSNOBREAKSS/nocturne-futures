import numpy as np
import pandas as pd
import pytest

from nocturne.research.validation import checked, reserve_holdout, walk_forward, block_mean_interval


def events(n=40):
    rows = []
    for day in pd.date_range("2026-01-01", periods=n, tz="UTC"):
        for target in range(3):
            rows.append({"day": day.date().isoformat(), "signal_id": str(day),
                         "feature_available_at": day, "label_end": day + pd.Timedelta("2D"),
                         "target": target})
    return pd.DataFrame(rows)


@pytest.mark.parametrize("rolling", [None, 12])
def test_purges_whole_signals_days_and_label_overlap(rolling):
    dev, final = reserve_holdout(events())
    folds = walk_forward(dev, min_train=10, calibration_groups=6, test_groups=4,
                         rolling_groups=rolling)
    assert folds
    for fold in folds:
        for left, right in ((fold.train, fold.calibration), (fold.calibration, fold.test)):
            assert left.label_end.max() + pd.Timedelta("1h") < right.feature_available_at.min()
            assert not set(left.signal_id) & set(right.signal_id)
            assert left.groupby("signal_id").size().eq(3).all()
        assert not set(fold.test.signal_id) & set(final.signal_id)
    assert dev.label_end.max() < final.feature_available_at.min()


def test_signal_crossing_groups_and_invalid_labels_rejected():
    data = events()
    data.loc[1, "day"] = "different"
    with pytest.raises(ValueError, match="signal spans"):
        checked(data)
    data = events()
    data.loc[0, "label_end"] = pd.Timestamp("2020-01-01", tz="UTC")
    with pytest.raises(ValueError, match="label ends"):
        checked(data)


def test_block_interval_keeps_repeated_targets_dependent():
    groups = np.repeat(np.arange(20), 3)
    values = np.repeat(np.arange(20) % 2, 3)
    first = block_mean_interval(values, groups)
    second = block_mean_interval(values, groups)
    assert first == second
    assert first["low"] <= 0.5 <= first["high"]
    assert first["groups"] == 20
