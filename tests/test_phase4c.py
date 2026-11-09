"""Phase 4C: authentic session dataset, labels, causality, caching and performance fixes."""
import numpy as np
import pandas as pd
import pytest

from nocturne.backtest.data import add_session_column
from nocturne.instruments import get_instrument
from nocturne.market_clock import session_date
from nocturne.studio import backtest, dataset, market, training

licensed = pytest.mark.skipif(not market.databento_available("NQ"), reason="licensed Databento data is local-only")


def test_vectorised_session_column_matches_reference():
    frame, _ = market.bars("NQ", "5m", limit=5000, source="yahoo")
    spec = get_instrument("NQ")
    fast = add_session_column(frame, spec)
    reference = [session_date(ts.to_pydatetime(), spec) for ts in frame.timestamp]
    assert list(fast.session) == reference


def test_synthetic_target_before_stop_labels():
    stamps = pd.date_range("2026-01-06 14:00", periods=6, freq="5min", tz="UTC")  # 09:00-09:25 ET = minutes 540..565
    def session(rows, minute0=600):
        ts = pd.date_range("2026-01-06 15:00", periods=len(rows), freq="5min", tz="UTC")
        return pd.DataFrame({"timestamp": ts, "open": [r[0] for r in rows], "high": [r[1] for r in rows], "low": [r[2] for r in rows],
                             "close": [r[3] for r in rows], "instrument_id": 7, "session": "D2", "rth": True,
                             "minute": [minute0 + 5 * i for i in range(len(rows))]})
    rows = pd.DataFrame({"next_session": ["D2"], "atr20_pts": [100.0], "contract_id": [7]}, index=[0])
    # long 0.5x0.25: target +50, stop -25 from entry 1000
    target_first = dataset._tbs(session([(1000, 1010, 995, 1005), (1005, 1055, 1000, 1050)]), rows)
    assert target_first["tbs_long_0.5x0.25"].iloc[0] == 1.0 and target_first["r_long_0.5x0.25"].iloc[0] == pytest.approx(2 - 0.75 / 25)
    tie = dataset._tbs(session([(1000, 1060, 970, 1000)]), rows)
    assert tie["tbs_long_0.5x0.25"].iloc[0] == 0.0  # same bar touches both: stop first
    timeout = dataset._tbs(session([(1000, 1010, 990, 1005), (1005, 1012, 995, 1010)]), rows)
    assert timeout["tbs_long_0.5x0.25"].iloc[0] == 0.0 and timeout["r_long_0.5x0.25"].iloc[0] == pytest.approx(10 / 25 - 0.75 / 25)
    other_contract = dataset._tbs(session([(1000, 1060, 995, 1050)]).assign(instrument_id=8), rows)
    assert np.isnan(other_contract["tbs_long_0.5x0.25"].iloc[0])
    late_open = dataset._tbs(session([(1000, 1060, 995, 1050)], minute0=605), rows)
    assert np.isnan(late_open["tbs_long_0.5x0.25"].iloc[0])
    del stamps


def test_databento_training_validation():
    base = {"source": "databento", "root": "NQ", "model": "logistic", "feature_families": ["price"]}
    assert training.validate({**base, "objective": "range_ge_points", "threshold_points": 123})
    assert training.validate({**base, "objective": "target_before_stop", "geometry": "9x9", "side": "long"})
    assert training.validate({**base, "objective": "expansion", "feature_families": ["intraday", "nonsense"]})
    assert training.validate({**base, "objective": "expansion", "feature_families": ["price", "intraday"]}) == []
    assert training.validate({**base, "source": "yahoo", "objective": "expansion"})  # authentic-only objective


@licensed
def test_session_dataset_labels_and_baselines_are_causal():
    data, meta = dataset.build("NQ")
    feature_cols = set(dataset.PRICE + dataset.INTRADAY)
    assert not any(c.startswith(("y_", "base_", "tbs_", "r_", "next_")) for c in feature_cols)
    same_next = data.contract_id.shift(-1) == data.contract_id
    expected = (data.close.shift(-1) > data.close).astype(float).where(same_next & data.next_range.notna())
    pd.testing.assert_series_equal(data.y_direction, expected, check_names=False)
    i = 2000
    window = data.y_direction.iloc[i - 250:i].dropna()
    assert data.base_direction.iloc[i] == pytest.approx(window.mean())
    assert data.loc[~same_next, "y_direction"].isna().all()  # no label across a roll


@licensed
def test_databento_cache_matches_normalized_table():
    frame, meta = market.bars("ES", "1h", limit=10_000_000, source="databento")
    store = pd.read_csv(market.DATABENTO / "ES_1h.csv.gz")
    assert len(frame) == len(store)
    assert (frame.close.to_numpy() == store.close.to_numpy()).all()
    assert (frame.contract.astype(str).to_numpy() == store.contract.astype(str).to_numpy()).all()
    assert meta["source"] == "databento"


def test_tp_fill_rates_are_nested(tmp_path):
    rule = {"side": "LONG", "conditions": [{"left": {"indicator": "close"}, "op": "crosses_above", "right": {"indicator": "vwap"}}],
            "stop": {"type": "atr", "value": 1.0}, "targets_r": [0.5, 1, 1.5], "horizon_bars": 24, "session": "ETH", "max_trades_per_session": 2}
    result = backtest.run({"name": "tp", "root": "NQ", "interval": "5m", "source": "yahoo", "contracts": 3, "strategy": {"type": "rule", "rule": rule}}, tmp_path)
    s = result["summary"]
    assert s["trades"] > 0 and 1 >= s["tp1_hit_rate"] >= s["tp2_hit_rate"] >= s["tp3_hit_rate"] >= 0
