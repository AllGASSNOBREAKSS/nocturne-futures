from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

from nocturne.forecast.replay import replay_at, save_replay
from nocturne.instruments import get_instrument


def test_future_mutation_cannot_change_frozen_forecast(tmp_path):
    source = Path(__file__).resolve().parents[1] / "data/market/intraday/NQ_5m.csv"
    frame = pd.read_csv(source).iloc[:2000].copy()
    asof = pd.Timestamp(frame.available_at.iloc[1500])
    frozen, outcome = replay_at(frame, get_instrument("NQ"), asof, include_bundle=False)
    mutated = frame.copy()
    for col in ("open", "high", "low", "close"):
        mutated.loc[1501:, col] += 1000
    second, new_outcome = replay_at(mutated, get_instrument("NQ"), asof, include_bundle=False)
    assert frozen == second
    assert outcome["v1"]["realized_high"] != new_outcome["v1"]["realized_high"]
    save_replay(tmp_path, frozen, outcome)
    save_replay(tmp_path, frozen, new_outcome)
    changed = deepcopy(frozen)
    changed["forecast"]["direction"] = "ALTERED"
    with pytest.raises(ValueError, match="immutable"):
        save_replay(tmp_path, changed, outcome)
