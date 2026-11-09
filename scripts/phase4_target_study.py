"""Phase 4: NQ target-before-stop on authentic Databento contract bars (2010 -> 2026).

Entry: first 5m bar open at/after 10:00 ET each session (after the opening range).
Geometries (points): 50/50, 100/50, 100/100, 200/100, 200/200, 350/175, 500/250.
Horizons: rest of RTH (to 16:00 ET) and 24 hours. Path on 5m bars of the SAME
contract; a 5m bar touching both levels is resolved with that contract's 1m
bars, and a 1m tie is STOP_FIRST. Sessions with a roll in the path are skipped.
Net = gross - 0.75 points (commission + 1 tick slippage each side, approx.).
Eras by date: development 2010-2018, validation 2019-2022, holdout 2023-2026.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from nocturne.studio import market

ROOT = Path(__file__).resolve().parents[1]
GEOMETRIES = [(50, 50), (100, 50), (100, 100), (200, 100), (200, 200), (350, 175), (500, 250)]
COST = 0.75
ERAS = {"development": (2010, 2018), "validation": (2019, 2022), "holdout": (2023, 2026)}


def first_hit(highs, lows, tp, sl, side):
    hit_t = (highs >= tp) if side > 0 else (lows <= tp)
    hit_s = (lows <= sl) if side > 0 else (highs >= sl)
    it = int(np.argmax(hit_t)) if hit_t.any() else None
    is_ = int(np.argmax(hit_s)) if hit_s.any() else None
    return it, is_


def wilson(k, n, z=1.96):
    if not n:
        return None
    p = k / n
    c = (p + z * z / (2 * n)) / (1 + z * z / n)
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return [round(c - h, 4), round(c + h, 4)]


def main():
    five, meta = market.bars("NQ", "5m", limit=10_000_000, source="databento")
    one, _ = market.bars("NQ", "1m", limit=50_000_000, source="databento")
    vix = market.archive().load("fred", "VIXCLS")
    vix = pd.Series(vix.value.to_numpy(), index=pd.to_datetime(vix.date)).sort_index()
    et = five.timestamp.dt.tz_convert("America/New_York")
    five["date"] = et.dt.date
    five["minute"] = et.dt.hour * 60 + et.dt.minute
    one_ts = one.timestamp.dt.tz_convert(None).to_numpy()  # naive UTC datetime64
    one_h, one_l, one_id = one.high.to_numpy(), one.low.to_numpy(), one.instrument_id.to_numpy()
    ts, hi, lo, cl, ins = five.timestamp.dt.tz_convert(None).to_numpy(), five.high.to_numpy(), five.low.to_numpy(), five.close.to_numpy(), five.instrument_id.to_numpy()
    rows = []
    entries = five[(five.minute >= 600) & (five.minute < 605) & (five.timestamp.dt.weekday < 5)]
    for i in entries.index:
        day = five.at[i, "date"]
        entry = float(five.at[i, "open"])
        contract = ins[i]
        rth_end = int(np.searchsorted(ts, (pd.Timestamp(day).tz_localize("America/New_York") + pd.Timedelta(hours=16)).tz_convert("UTC").tz_localize(None).to_datetime64()))
        day_end = int(np.searchsorted(ts, ts[i] + np.timedelta64(24, "h")))
        prior = vix[vix.index < pd.Timestamp(day)]
        regime_vix = float(prior.iloc[-1]) if len(prior) else np.nan
        for horizon, end in (("RTH", rth_end), ("24H", day_end)):
            if end <= i or (ins[i:end] != contract).any():
                continue  # roll inside the path: skip, never stitch contracts
            h, l = hi[i:end], lo[i:end]
            for target, stop in GEOMETRIES:
                for side in (1, -1):
                    tp, sl = entry + side * target, entry - side * stop
                    it, is_ = first_hit(h, l, tp, sl, side)
                    resolution = "5m"
                    if it is not None and (is_ is None or it < is_):
                        outcome, k = "TARGET_FIRST", it
                    elif is_ is not None and (it is None or is_ < it):
                        outcome, k = "STOP_FIRST", is_
                    elif it is not None:  # same 5m bar: resolve inside with 1m bars of the same contract
                        k = it
                        a = int(np.searchsorted(one_ts, ts[i + k]))
                        b = int(np.searchsorted(one_ts, ts[i + k] + np.timedelta64(5, "m")))
                        mask = one_id[a:b] == contract
                        sub_t, sub_s = first_hit(one_h[a:b][mask], one_l[a:b][mask], tp, sl, side)
                        if sub_t is not None and (sub_s is None or sub_t < sub_s):
                            outcome, resolution = "TARGET_FIRST", "1m"
                        else:
                            outcome, resolution = "STOP_FIRST", "1m" if sub_s is not None and sub_t != sub_s else "AMBIGUOUS_STOP_FIRST"
                    else:
                        outcome, k = "TIMEOUT", end - i - 1
                    gross = target if outcome == "TARGET_FIRST" else -stop if outcome == "STOP_FIRST" else (cl[end - 1] - entry) * side
                    rows.append((day.year, str(day), horizon, target, stop, "LONG" if side > 0 else "SHORT", outcome, resolution,
                                 k + 1, gross - COST, regime_vix, entry))
    data = pd.DataFrame(rows, columns=["year", "date", "horizon", "target", "stop", "side", "outcome", "resolution", "bars", "net", "vix", "entry"])
    out = {"generated_at": datetime.now(timezone.utc).isoformat(), "data": meta["dataset"], "sessions": int(data.date.nunique()),
           "records": int(len(data)), "method": __doc__.strip(), "cells": []}
    for (horizon, target, stop, side), g in data.groupby(["horizon", "target", "stop", "side"]):
        cell = {"horizon": horizon, "target": int(target), "stop": int(stop), "side": side}
        for era, (a, b) in ERAS.items():
            f = g[g.year.between(a, b)]
            n = len(f)
            k = int((f.outcome == "TARGET_FIRST").sum())
            se = f.net.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
            cell[era] = {"n": n, "target_first": round(k / n, 4) if n else None, "target_first_ci95": wilson(k, n),
                         "stop_first": round(float((f.outcome == "STOP_FIRST").mean()), 4) if n else None,
                         "timeout": round(float((f.outcome == "TIMEOUT").mean()), 4) if n else None,
                         "median_bars_to_target": float(f[f.outcome == "TARGET_FIRST"].bars.median()) if k else None,
                         "net_ev_points": round(float(f.net.mean()), 3) if n else None,
                         "net_ev_ci95": [round(float(f.net.mean() - 1.96 * se), 3), round(float(f.net.mean() + 1.96 * se), 3)] if n > 1 else None,
                         "median_entry_level": float(f.entry.median()) if n else None,
                         "ambiguous_ties": int((f.resolution == "AMBIGUOUS_STOP_FIRST").sum())}
        d, h = cell["development"], cell["holdout"]
        cell["verdict"] = ("CANDIDATE_RESEARCH_ONLY" if d["n"] >= 100 and h["n"] >= 100 and d["net_ev_ci95"] and h["net_ev_ci95"]
                           and d["net_ev_ci95"][0] > 0 and h["net_ev_ci95"][0] > 0 else "REJECTED")
        cell["by_vix"] = {name: round(float((g[m].outcome == "TARGET_FIRST").mean()), 4) if m.sum() else None
                          for name, m in (("vix<15", g.vix < 15), ("15-25", g.vix.between(15, 25)), ("vix>25", g.vix > 25))}
        out["cells"].append(cell)
    (ROOT / "reports/phase4_target_study.json").write_text(json.dumps(out, indent=2, default=str) + "\n")
    print(out["sessions"], out["records"], sum(c["verdict"] != "REJECTED" for c in out["cells"]), "accepted of", len(out["cells"]))
    for c in out["cells"]:
        d, h = c["development"], c["holdout"]
        print(c["horizon"], c["target"], c["stop"], c["side"], d["n"], d["target_first"], d["net_ev_points"], d["net_ev_ci95"], "|", h["n"], h["target_first"], h["net_ev_points"], h["net_ev_ci95"], c["verdict"])


if __name__ == "__main__":
    main()
