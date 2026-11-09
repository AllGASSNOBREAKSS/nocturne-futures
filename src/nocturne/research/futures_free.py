"""Phase 3V zero-cost futures research on Yahoo continuous NQ=F/ES=F history.

Data: Yahoo continuous front-month (unadjusted, research-grade), validated to
cover the Globex session (prior 18:00 ET to 17:00 ET); its daily close behaves
like a settlement price. Roll dates come from Databento's free symbology
metadata (volume roll of NQ.v.0/ES.v.0); sessions within +/-3 trading days of
a roll are excluded from labels. Free macro/positioning features use the
Phase 3U point-in-time join. Nothing here is raw-contract, tick or order-flow
data. The protocol is fixed before scoring.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from ..collector.store import Archive
from .free_data_experiment import FREE, block_bootstrap, direction_metrics, free_features

PROTOCOL = {
    "version": "phase3v-free-futures-v1", "test_years": list(range(2008, 2027)),
    "development_years": list(range(2008, 2024)), "holdout_years": [2024, 2025, 2026],
    "holdout_note": "2024+ NQ history was inspected in earlier phases with other methods; scored once here",
    "embargo_days": 5, "calibration_rows": 250, "C": 0.2, "seed": 7, "roll_exclusion_sessions": 3,
    "large_move_points": [100, 200, 350, 500], "compression_atr_fraction": 0.6, "trailing_window": 250,
    "tbs_geometries": [(100, 100), (200, 100), (200, 200), (350, 175), (500, 250)],
    "tbs_entry": "open of the 15:00 UTC hourly bar (10:00/11:00 ET)", "tbs_horizon_bars": [6, 24],
    "tbs_cost_points": 0.75, "tbs_split": "first 60% of sessions development, last 40% holdout",
    "verdict": ("ACCEPT only if Brier beats the trailing baseline with a 95% monthly block-bootstrap CI below "
                "zero in development AND the holdout mean difference is also negative; REJECT if development CI "
                "is above zero; otherwise INCONCLUSIVE"),
}
FAMILIES = {"volatility": ["vix", "vix_chg5", "vxn_minus_vix"],
            "rates_credit": ["t10y2y", "dgs10_chg5", "baa10y", "baa10y_chg20", "walcl_chg13", "usd_chg20"],
            "positioning": ["cot_nq_am_net", "cot_nq_am_net_chg4", "cot_nq_lev_net", "cot_es_am_net"],
            "filings": ["megacap_filings_5d"]}
PRICE = ["ret_1", "ret_5", "ret_20", "vol_20", "range_pts", "atr20_pts", "range_atr", "log_level", "pos_20"]


def roll_dates(preflight_report: Path, metadata_root: Path, symbol: str):
    report = json.loads(Path(preflight_report).read_text())
    receipt = next(r for r in report["metadata_receipts"] if r["method"] == "symbology.resolve")
    body = (Path(metadata_root) / "objects" / receipt["body_sha256"]).read_bytes()
    import hashlib
    if hashlib.sha256(body).hexdigest() != receipt["body_sha256"]:
        raise ValueError("symbology receipt checksum mismatch")
    intervals = json.loads(body)["result"][symbol]
    return sorted(pd.Timestamp(i["d0"]).date() for i in intervals[1:])


def daily_frame(archive: Archive, root: str, rolls):
    bars = archive.load("yahoo_futures", f"{root}_1d")
    bars["timestamp"] = pd.to_datetime(bars.timestamp, utc=True)
    bars["date"] = bars.timestamp.dt.tz_convert("America/New_York").dt.date
    bars = bars[bars.ohlc_consistent.astype(bool)].sort_values("date").reset_index(drop=True)
    # Feature cutoff: one minute before the next Globex session opens (18:00 ET).
    et = pd.to_datetime(bars.date.astype(str)).dt.tz_localize("America/New_York") + pd.Timedelta(hours=18) - pd.Timedelta(minutes=1)
    bars["cutoff"] = et.dt.tz_convert("UTC")
    near = np.zeros(len(bars), bool)
    for roll in rolls:
        position = np.searchsorted(np.array(bars.date), roll)
        near[max(0, position - PROTOCOL["roll_exclusion_sessions"]):position + PROTOCOL["roll_exclusion_sessions"] + 1] = True
    bars["near_roll"] = near
    c, h, l = bars.close, bars.high, bars.low
    rng = h - l
    out = pd.DataFrame({"date": bars.date, "cutoff": bars.cutoff, "near_roll": bars.near_roll, "close": c,
                        "ret_1": c.pct_change(fill_method=None), "ret_5": c / c.shift(5) - 1, "ret_20": c / c.shift(20) - 1,
                        "range_pts": rng, "atr20_pts": rng.rolling(20).mean(), "log_level": np.log(c),
                        "pos_20": (c - l.rolling(20).min()) / (h.rolling(20).max() - l.rolling(20).min())})
    out["vol_20"] = out.ret_1.rolling(20).std()
    out["range_atr"] = out.range_pts / out.atr20_pts
    # Return features spanning a roll include the unadjusted contract basis
    # (documented limitation); labels near rolls are excluded below.
    nxt = lambda s: s.shift(-1)
    out["next_range"] = nxt(rng)
    out["next_near_roll"] = nxt(out.near_roll).fillna(True).astype(bool)
    out["next_up"] = (nxt(c) > c).astype(float).where(nxt(c).notna())
    out["next_up_exc"] = nxt(h) - c
    out["next_dn_exc"] = c - nxt(l)
    for n in PROTOCOL["large_move_points"]:
        out[f"y_range_{n}"] = (out.next_range >= n).astype(float).where(out.next_range.notna())
        out[f"base_range_{n}"] = (out.range_pts >= n).astype(float).rolling(PROTOCOL["trailing_window"]).mean()
    out["y_compress"] = (out.next_range < PROTOCOL["compression_atr_fraction"] * out.atr20_pts).astype(float).where(out.next_range.notna())
    out["base_compress"] = (out.range_pts < PROTOCOL["compression_atr_fraction"] * out.atr20_pts.shift(1)).astype(float).rolling(PROTOCOL["trailing_window"]).mean()
    out["base_up"] = (c > c.shift(1)).astype(float).rolling(PROTOCOL["trailing_window"]).mean()
    free, audit = free_features(archive, out.cutoff.reset_index(drop=True))
    out = pd.concat([out.reset_index(drop=True), free], axis=1)
    out["year"] = pd.to_datetime(out.date).dt.year
    return out[~out.next_near_roll & ~out.near_roll].reset_index(drop=True), audit, int(bars.near_roll.sum())


def walk_forward(data, label, base_col, features, lgbm=False):
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from ..ml.calibration import PlattCalibrator
    usable = data.dropna(subset=features + [label, base_col])
    rows = []
    for year in PROTOCOL["test_years"]:
        test = usable[usable.year == year]
        start = pd.Timestamp(f"{year}-01-01")
        train = usable[pd.to_datetime(usable.date) < start - pd.Timedelta(days=PROTOCOL["embargo_days"])]
        if test.empty or len(train) < 750 or train[label].nunique() < 2:
            continue
        fit, cal = train.iloc[:-PROTOCOL["calibration_rows"]], train.iloc[-PROTOCOL["calibration_rows"]:]
        if fit[label].nunique() < 2 or cal[label].nunique() < 2:
            continue
        if lgbm:
            from lightgbm import LGBMClassifier
            model = LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=15, min_child_samples=50,
                                   subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=PROTOCOL["seed"], verbose=-1)
        else:
            model = make_pipeline(StandardScaler(), LogisticRegression(C=PROTOCOL["C"], max_iter=2000))
        model.fit(fit[features], fit[label])
        platt = PlattCalibrator().fit(model.predict_proba(cal[features])[:, 1], cal[label].to_numpy())
        rows.append(pd.DataFrame({"date": test.date, "year": year, "y": test[label].to_numpy(),
                                  "p_model": platt.predict(model.predict_proba(test[features])[:, 1]),
                                  "p_base": test[base_col].clip(1e-4, 1 - 1e-4).to_numpy(), "vix": test.vix.to_numpy()}))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()


def score(pred):
    out = {}
    for era, years in (("development", PROTOCOL["development_years"]), ("holdout", PROTOCOL["holdout_years"])):
        frame = pred[pred.year.isin(years)].reset_index(drop=True)
        if frame.empty or frame.y.nunique() < 2:
            out[era] = {"n": len(frame), "status": "INSUFFICIENT_CLASSES"}
            continue
        y = frame.y.to_numpy()
        diff = block_bootstrap(frame, (frame.p_model - y) ** 2, (frame.p_base - y) ** 2, 2000, PROTOCOL["seed"])
        out[era] = {"model": direction_metrics(y, frame.p_model), "trailing_baseline": direction_metrics(y, frame.p_base),
                    "brier_model_minus_baseline": diff, "ece_model": ece(y, frame.p_model.to_numpy())}
    dev, hold = out.get("development", {}), out.get("holdout", {})
    if "brier_model_minus_baseline" not in dev:
        verdict = "INCONCLUSIVE"
    elif dev["brier_model_minus_baseline"]["ci95"][0] > 0:
        verdict = "REJECT"
    elif dev["brier_model_minus_baseline"]["ci95"][1] < 0 and hold.get("brier_model_minus_baseline", {}).get("mean", 1) < 0:
        verdict = "ACCEPT_RESEARCH_ONLY"
    else:
        verdict = "INCONCLUSIVE"
    out["verdict"] = verdict
    return out


def increment(pred, reference):
    """Brier(candidate) - Brier(reference) on sessions both models scored."""
    merged = pred.merge(reference[["date", "p_model"]], on="date", suffixes=("", "_ref"))
    out = {}
    for era, years in (("development", PROTOCOL["development_years"]), ("holdout", PROTOCOL["holdout_years"])):
        frame = merged[merged.year.isin(years)].reset_index(drop=True)
        if frame.empty:
            out[era] = {"n": 0, "mean": float("nan"), "ci95": [float("nan")] * 2}
            continue
        y = frame.y.to_numpy()
        out[era] = {"n": len(frame), **block_bootstrap(frame, (frame.p_model - y) ** 2, (frame.p_model_ref - y) ** 2, 2000, PROTOCOL["seed"])}
    dev, hold = out["development"], out["holdout"]
    out["verdict"] = ("FAMILY_HELPS" if dev["ci95"][1] < 0 and hold["mean"] < 0 else
                      "FAMILY_HURTS" if dev["ci95"][0] > 0 else "NO_DETECTABLE_INCREMENT")
    return out


def ece(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges) - 1, 0, bins - 1)
    return float(sum(abs(y[idx == b].mean() - p[idx == b].mean()) * (idx == b).mean() for b in range(bins) if (idx == b).any()))


def large_move_table(data):
    """Empirical next-session frequencies by VIX regime and era (no model)."""
    regimes = {"vix<15": data.vix < 15, "15<=vix<=25": data.vix.between(15, 25), "vix>25": data.vix > 25}
    eras = {"2008-2015": data.year.between(2008, 2015), "2016-2023": data.year.between(2016, 2023), "2024-2026": data.year >= 2024}
    table = {}
    for era, em in eras.items():
        for regime, rm in regimes.items():
            frame = data[em & rm]
            cell = {"sessions": int(len(frame)), "median_range_pts": float(frame.next_range.median()) if len(frame) else None,
                    "median_level": float(frame.close.median()) if len(frame) else None}
            for n in PROTOCOL["large_move_points"]:
                k = int((frame.next_range >= n).sum())
                cell[f"range_ge_{n}"] = wilson(k, len(frame))
                cell[f"up_exc_ge_{n}"] = wilson(int((frame.next_up_exc >= n).sum()), len(frame))
                cell[f"down_exc_ge_{n}"] = wilson(int((frame.next_dn_exc >= n).sum()), len(frame))
            table[f"{era} | {regime}"] = cell
    return table


def wilson(k, n, z=1.96):
    if n == 0:
        return {"k": 0, "n": 0, "p": None, "ci95": None}
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return {"k": k, "n": n, "p": round(p, 4), "ci95": [round(max(0, centre - half), 4), round(min(1, centre + half), 4)]}


def target_before_stop(archive: Archive, root: str, rolls, vix_by_date):
    """Hourly symmetric-entry geometry study; same-bar touches resolved by 5m/1m where available,
    otherwise conservatively STOP_FIRST. Timeouts are marked to market at the last bar close."""
    hourly = archive.load("yahoo_futures", f"{root}_60m")
    hourly["timestamp"] = pd.to_datetime(hourly.timestamp, utc=True)
    hourly = hourly[hourly.ohlc_consistent.astype(bool)].sort_values("timestamp").reset_index(drop=True)
    fine = {}
    for interval in ("1m", "5m"):
        f = archive.load("yahoo_futures", f"{root}_{interval}")
        f["timestamp"] = pd.to_datetime(f.timestamp, utc=True)
        fine[interval] = f.sort_values("timestamp").reset_index(drop=True)
    hourly["date"] = hourly.timestamp.dt.tz_convert("America/New_York").dt.date
    roll_set = set()
    days = sorted(hourly.date.unique())
    for roll in rolls:
        position = np.searchsorted(np.array(days), roll)
        roll_set.update(days[max(0, position - 3):position + 4])
    entries = hourly[(hourly.timestamp.dt.hour == 15) & ~hourly.date.isin(roll_set)]
    records = []
    for i, entry in entries.iterrows():  # index == position after reset_index
        price = float(entry.open)
        prior_vix = vix_by_date.loc[:pd.Timestamp(entry.date) - pd.Timedelta(days=1)]
        vix = float(prior_vix.iloc[-1]) if len(prior_vix) else np.nan
        for horizon in PROTOCOL["tbs_horizon_bars"]:
            path = hourly.iloc[i:i + horizon]
            if len(path) < horizon or (path.timestamp.diff().dropna() > pd.Timedelta(hours=3)).any() and horizon == 6:
                continue
            for target, stop in PROTOCOL["tbs_geometries"]:
                for side in ("LONG", "SHORT"):
                    outcome, resolution, bars = resolve(path, fine, price, target, stop, side)
                    pnl = (target if outcome == "TARGET_FIRST" else -stop if outcome == "STOP_FIRST"
                           else (path.close.iloc[-1] - price) * (1 if side == "LONG" else -1))
                    records.append({"date": entry.date, "horizon_bars": horizon, "target": target, "stop": stop,
                                    "side": side, "outcome": outcome, "resolution": resolution, "bars_to_exit": bars,
                                    "gross_points": float(pnl), "net_points": float(pnl) - PROTOCOL["tbs_cost_points"], "vix": vix})
    return pd.DataFrame(records)


def resolve(path, fine, price, target, stop, side):
    sign = 1 if side == "LONG" else -1
    tp, sl = price + sign * target, price - sign * stop
    for k, (_, bar) in enumerate(path.iterrows()):
        hit_t = bar.high >= tp if side == "LONG" else bar.low <= tp
        hit_s = bar.low <= sl if side == "LONG" else bar.high >= sl
        if hit_t and hit_s:
            for interval in ("1m", "5m"):
                f = fine[interval]
                window = f[(f.timestamp >= bar.timestamp) & (f.timestamp < bar.timestamp + pd.Timedelta(hours=1))]
                expected = 60 if interval == "1m" else 12
                if len(window) >= 0.9 * expected:
                    for _, sub in window.iterrows():
                        st = sub.high >= tp if side == "LONG" else sub.low <= tp
                        ss = sub.low <= sl if side == "LONG" else sub.high >= sl
                        if st and ss:
                            return "STOP_FIRST", f"AMBIGUOUS_{interval}_STOP_FIRST", k + 1
                        if ss:
                            return "STOP_FIRST", f"RESOLVED_{interval}", k + 1
                        if st:
                            return "TARGET_FIRST", f"RESOLVED_{interval}", k + 1
            return "STOP_FIRST", "AMBIGUOUS_HOURLY_STOP_FIRST", k + 1
        if hit_s:
            return "STOP_FIRST", "HOURLY", k + 1
        if hit_t:
            return "TARGET_FIRST", "HOURLY", k + 1
    return "TIMEOUT", "HOURLY", len(path)


def tbs_summary(records):
    days = sorted(records.date.unique())
    cut = days[int(len(days) * 0.6)]
    out = []
    for (h, t, s, side), g in records.groupby(["horizon_bars", "target", "stop", "side"]):
        row = {"horizon_bars": int(h), "target": int(t), "stop": int(s), "side": side}
        for era, frame in (("development", g[g.date < cut]), ("holdout", g[g.date >= cut])):
            n = len(frame)
            net = frame.net_points.to_numpy()
            se = net.std(ddof=1) / np.sqrt(n) if n > 1 else np.nan
            row[era] = {"n": n, "target_first": wilson(int((frame.outcome == "TARGET_FIRST").sum()), n),
                        "stop_first_pct": round(float((frame.outcome == "STOP_FIRST").mean()), 4) if n else None,
                        "timeout_pct": round(float((frame.outcome == "TIMEOUT").mean()), 4) if n else None,
                        "ambiguous_conservative": int(frame.resolution.str.startswith("AMBIGUOUS").sum()),
                        "resolved_by_fine_bars": int(frame.resolution.str.startswith("RESOLVED").sum()),
                        "net_ev_points": round(float(net.mean()), 3) if n else None,
                        "net_ev_ci95": [round(float(net.mean() - 1.96 * se), 3), round(float(net.mean() + 1.96 * se), 3)] if n > 1 else None,
                        "by_vix": {name: {"n": int(m.sum()), "target_first": round(float((frame.outcome[m] == "TARGET_FIRST").mean()), 4) if m.sum() else None}
                                   for name, m in (("vix<15", frame.vix < 15), ("15-25", frame.vix.between(15, 25)), ("vix>25", frame.vix > 25))}}
        dev, hold = row["development"], row["holdout"]
        row["status"] = ("CANDIDATE_RESEARCH_ONLY" if dev["n"] >= 30 and hold["n"] >= 30 and dev["net_ev_ci95"] and hold["net_ev_ci95"]
                         and dev["net_ev_ci95"][0] > 0 and hold["net_ev_ci95"][0] > 0 else "REJECTED")
        out.append(row)
    return out, str(cut)
