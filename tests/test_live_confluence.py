"""Session levels, confluence, RR/contract backtests, model signals and news parsing."""
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pytest

from nocturne.strategies.base import Signal, TargetSpec
from nocturne.studio import backtest, market, news, sessions, sweep

licensed = pytest.mark.skipif(not market.databento_available("NQ"), reason="licensed Databento data is local-only")


def _session(day="2026-03-10", base=100.0):
    """Synthetic 5m Globex session: Asia 90-110, London 95-120, NY trend to 140."""
    start = pd.Timestamp(f"{day} 18:00", tz=sessions.ET) - pd.Timedelta(days=1)
    ts = pd.date_range(start, periods=23 * 12, freq="5min")
    minute = ts.hour * 60 + ts.minute
    price = np.where((minute >= 18 * 60) | (minute < 180), base, np.where(minute < 570, base + 10, base + 30))
    f = pd.DataFrame({"timestamp": ts.tz_convert("UTC"), "open": price, "high": price + 2, "low": price - 2, "close": price, "volume": 100.0})
    return sessions.annotate(f)


def test_levels_never_use_bars_after_cutoff():
    prior, cur = _session("2026-03-09"), _session("2026-03-10")
    hist = pd.DataFrame({"high": [130.0] * 30, "low": [80.0] * 30, "close": [100.0] * 30})
    at_open = sessions.levels_at(prior, cur, hist, sessions.CUTOFFS["ny_open"], 0.25, 4)
    # NY prints 130-132 after 09:30; nothing known at 09:30 may reflect it
    assert at_open["LON_H"] == 112.0 and at_open["ASIA_H"] == 102.0
    assert "ORB30_H" not in at_open and "IB_H" not in at_open
    assert at_open["VWAP"] < 112
    after_ib = sessions.levels_at(prior, cur, hist, sessions.CUTOFFS["post_ib"], 0.25, 4)
    assert after_ib["ORB30_H"] == 132.0 and after_ib["IB_L"] == 128.0
    # Truncating the session after the cutoff must not change any level
    truncated = cur[sessions.elapsed(cur.minute.to_numpy(), sessions.CUTOFFS["post_ib"])]
    assert sessions.levels_at(prior, truncated, hist, sessions.CUTOFFS["post_ib"], 0.25, 4) == after_ib


def test_session_windows_and_annotation():
    cur = _session()
    assert cur.session.nunique() == 1 and cur.session.iloc[0] == "2026-03-10"
    assert not ((cur.minute >= 17 * 60) & (cur.minute < 18 * 60)).any()  # maintenance hour dropped


def test_profile_and_confluence():
    bars = pd.DataFrame({"high": [101.0, 102, 101], "low": [99.0, 100, 99], "volume": [10.0, 50, 10]})
    poc, vah, val = sessions.profile(bars, 0.25, 4)
    assert val <= poc <= vah and 100 <= poc <= 102
    conf = sessions.confluence({"PDH": 100.0, "ASIA_H": 100.4, "PIV_R1": 100.2, "W20_H": 150.0}, 0.5)
    assert conf["PDH"]["count"] == 2 and conf["W20_H"]["count"] == 0
    assert conf["PDH"]["groups"] == 2  # session + indicator, own group excluded


def test_contract_schedule_is_whole_contracts():
    for contracts in range(1, 51):
        for n in (1, 2, 3):
            sched = backtest.schedule_for(contracts, n)
            assert abs(sum(f for _, f in sched) - 1) < 1e-9
            assert all(abs(f * contracts - round(f * contracts)) < 1e-9 for _, f in sched)
    assert backtest.schedule_for(5, 3) == ((0, 0.4), (1, 0.4), (2, 0.2))


def test_apply_exit_rewrites_targets_as_rr():
    s = Signal("x", "1", "NQ", datetime(2026, 1, 2, tzinfo=timezone.utc), "LONG", 100.0, 100.0, 90.0,
               (TargetSpec("TP1", 105.0, 0.5),), 10, ("t",))
    [(day, out)] = backtest.apply_exit([("d", s)], {"rr": [3, 8]})
    assert [t.price for t in out.targets] == [130.0, 180.0] and out.stop == 90.0
    [(day, pts)] = backtest.apply_exit([("d", s)], {"rr": [2], "stop": {"type": "points", "value": 4}})
    assert pts.stop == 96.0 and pts.targets[0].price == 108.0


def test_validation_limits():
    base = {"root": "NQ", "interval": "5m", "strategy": {"type": "opening_range_breakout"}}
    assert backtest.validate({**base, "contracts": 50}) == []
    assert any("contracts" in e for e in backtest.validate({**base, "contracts": 51}))
    assert any("exit.rr" in e for e in backtest.validate({**base, "exit": {"rr": [8, 3]}}))
    assert any("points stop" in e for e in backtest.validate({**base, "exit": {"rr": [3], "stop": {"type": "atr", "value": 1}}}))
    assert sweep.validate({"root": "NQ", "rr": [1, 3, 8], "contracts": 10}) == []
    assert sweep.validate({"root": "XX", "rr": [99]})


def test_news_parsing_offline(monkeypatch):
    rss = b"""<rss><channel>
      <item><title>Fed signals rate cut as inflation cools</title><link>https://a/1</link><pubDate>Mon, 09 Nov 2026 14:00:00 GMT</pubDate></item>
      <item><title>Missile attack escalates conflict</title><link>https://a/2</link><pubDate>Mon, 09 Nov 2026 13:00:00 GMT</pubDate></item>
    </channel></rss>"""

    class R:
        content = rss
        def raise_for_status(self):
            return None
    monkeypatch.setattr(news, "FEEDS", {"Test": "https://example.invalid/rss"})
    monkeypatch.setattr(news, "_get", lambda url, timeout=12: R())
    news._cache.clear()
    items = news.headlines()["items"]
    assert [i["tone"] for i in items] == ["positive", "negative"]
    assert "Fed & rates" in items[0]["categories"] and "Geopolitics" in items[1]["categories"]
    news._cache.clear()


@licensed
def test_model_signals_are_out_of_sample():
    from nocturne.studio import levelmodel, modelsignals
    oos = pd.read_csv(levelmodel.oos_path("NQ"))
    first_test_year = int(oos.year.min())
    rows, _ = levelmodel.build("NQ")
    assert first_test_year > int(rows.year.min())  # first years only ever train
    sig = modelsignals.signals("ml_levels", {"cutoff": "ny_open", "min_probability": 0.6}, "NQ", {"rr": [2]})
    assert sig and all(int(day[:4]) >= first_test_year for day, _ in sig)
    day, s = sig[0]
    risk, reward = abs(s.entry_high - s.stop), abs(s.targets[0].price - s.entry_high)
    assert reward / risk == pytest.approx(2, rel=1e-3)
    assert pd.Timestamp(s.asof).tz_convert(sessions.ET).strftime("%H:%M") == "09:30"


@licensed
def test_level_model_beats_distance_baseline():
    from nocturne.studio import levelmodel
    r = levelmodel.study("NQ")
    assert r["auc"] > r["auc_distance_only"] and r["brier"] < r["brier_distance_only"]
    for b in r["calibration"]:
        if b["n"] > 5000:
            assert abs(b["predicted"] - b["hit_rate"]) < 0.06, b
