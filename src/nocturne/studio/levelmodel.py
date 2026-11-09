"""Which levels get traded? A walk-forward level-touch model on authentic contract bars.

For every Databento session and three cutoffs (03:00, 09:30, 10:30 ET) we collect every
level known at the cutoff (sessions.levels_at, incl. out-of-sample ML projections) and label
whether price trades it before 16:00 ET. Roll sessions are excluded (prior-session levels
would belong to a different contract). A LightGBM classifier is refit every year (train on
earlier years only); the out-of-sample probabilities give the calibration table the app
shows. Same dataset also measures the intraday state -> rest-of-day direction question.
"""
from __future__ import annotations

import hashlib
import json

import joblib
import numpy as np
import pandas as pd

from ..instruments import get_instrument
from ..shadow.locking import FileLock
from . import STATE, market, predictor, sessions

DIR = STATE / "levelmodel"
VERSION = "levels-v2"
TYPES = list(sessions.LEVEL_NAMES)
FEATURES = ["dist_atr", "abs_atr", "above", "type", "conf_count", "conf_groups", "traded_before", "cutoff",
            "gap_atr", "range_so_far_atr", "vs_vwap", "atr_pct"]
BIN_TICKS = {"NQ": 8, "ES": 2}


def _key(root):
    manifest = json.loads((market.DATABENTO / "manifest.json").read_text())
    return hashlib.sha256(f"{VERSION}|{manifest[root + '_5m']['sha256']}|{predictor._key(root)}".encode()).hexdigest()[:16]


def _ml_levels(root):
    path = predictor.oos_path(root)
    if not path.exists():
        return {}
    oos = pd.read_csv(path)
    out = {}
    for g in oos.to_dict("records"):
        out[g["date"]] = {"ML_UP50": g["close"] + g["up_q0.5"] * g["atr"], "ML_UP25": g["close"] + g["up_q0.75"] * g["atr"],
                          "ML_DN50": g["close"] - g["dn_q0.5"] * g["atr"], "ML_DN25": g["close"] - g["dn_q0.75"] * g["atr"]}
    return out


def daily_from(annotated):
    g = annotated.groupby("session", sort=True)
    return pd.DataFrame({"high": g.high.max(), "low": g.low.min(), "close": g.close.last(), "open": g.open.first(),
                         "first_id": g.instrument_id.first() if "instrument_id" in annotated else 0,
                         "last_id": g.instrument_id.last() if "instrument_id" in annotated else 0})


def atr20(daily):
    prev = daily.close.shift(1)
    tr = np.maximum(daily.high - daily.low, np.maximum((daily.high - prev).abs(), (daily.low - prev).abs()))
    return tr.rolling(20, min_periods=20).mean()


def rows_for_session(root, prior, current, history, atr, ml, cutoff_name):
    """Feature rows (and labels when the session is complete) for one session and cutoff."""
    spec = get_instrument(root)
    cutoff = sessions.CUTOFFS[cutoff_name]
    lv = sessions.levels_at(prior, current, history, cutoff, spec.tick_size, BIN_TICKS[root], ml)
    before = current[sessions.elapsed(current.minute.to_numpy(), cutoff)]
    after = current[~sessions.elapsed(current.minute.to_numpy(), cutoff) & (sessions._rel(current.minute.to_numpy()) < sessions._rel(sessions.NY_CLOSE))]
    if before.empty or not lv:
        return [], None
    price = float(before.close.iloc[-1])
    conf = sessions.confluence(lv, 0.1 * atr)
    state = sessions.session_state(current, cutoff)
    common = {"cutoff": list(sessions.CUTOFFS).index(cutoff_name), "gap_atr": (float(before.open.iloc[0]) - lv.get("PDC", price)) / atr,
              "range_so_far_atr": float(before.high.max() - before.low.min()) / atr, "vs_vwap": state.get("vs_vwap") or 0.0,
              "atr_pct": atr / price}
    hi_after = float(after.high.max()) if not after.empty else np.nan
    lo_after = float(after.low.min()) if not after.empty else np.nan
    out = []
    for key, level in lv.items():
        row = {"key": key, "price": level, "ref": price, "dist_atr": (level - price) / atr, "abs_atr": abs(level - price) / atr,
               "above": int(level >= price), "type": TYPES.index(key), "conf_count": conf[key]["count"], "conf_groups": conf[key]["groups"],
               "traded_before": int(before.low.min() <= level <= before.high.max()), **common}
        if not after.empty:
            row["y"] = int(min(lo_after, price) <= level <= max(hi_after, price))
        out.append(row)
    label = None
    if not after.empty and after.minute.iloc[-1] >= sessions.NY_CLOSE - 10:
        label = {"price": price, "close": float(after.close.iloc[-1]), **common, "orb": state.get("orb")}
    return out, label


def build(root):
    """Historical (session, cutoff, level) rows from authentic 5m bars. Cached on disk."""
    DIR.mkdir(parents=True, exist_ok=True)
    path, spath = DIR / f"{root}_{_key(root)}_rows.csv", DIR / f"{root}_{_key(root)}_state.csv"
    if path.exists() and spath.exists():
        return pd.read_csv(path), pd.read_csv(spath)
    five, _ = market.bars(root, "5m", limit=50_000_000, source="databento")
    bars = sessions.annotate(five)
    groups = {s: g for s, g in bars.groupby("session", sort=True)}
    daily = daily_from(bars)
    atr = atr20(daily)
    ml = _ml_levels(root)
    days = list(daily.index)
    rows, states = [], []
    for i in range(1, len(days)):
        day, prev = days[i], days[i - 1]
        if daily.first_id.iloc[i] != daily.last_id.iloc[i - 1] or not np.isfinite(atr.iloc[i - 1]):
            continue  # roll: prior-session levels belong to another contract
        hist = daily.iloc[:i]
        for name in sessions.CUTOFFS:
            r, s = rows_for_session(root, groups[prev], groups[day], hist, float(atr.iloc[i - 1]), ml.get(prev), name)
            for x in r:
                x.update(session=day, year=int(day[:4]))
            rows += r
            if s:
                states.append({**s, "session": day, "year": int(day[:4]), "cutoff_name": name})
    frame, state = pd.DataFrame(rows), pd.DataFrame(states)
    frame.to_csv(path, index=False)
    state.to_csv(spath, index=False)
    return frame, state


def _model():
    from lightgbm import LGBMClassifier
    return LGBMClassifier(n_estimators=300, learning_rate=0.05, num_leaves=31, min_child_samples=200, subsample=0.8, subsample_freq=1,
                          colsample_bytree=0.9, random_state=7, verbose=-1)


def _fit(train, features):
    from ..ml.calibration import PlattCalibrator
    cut = train.session.sort_values().unique()
    cal_start = cut[int(len(cut) * 0.85)]
    fit_rows, cal_rows = train[train.session < cal_start], train[train.session >= cal_start]
    model = _model().fit(fit_rows[features], fit_rows.y, categorical_feature=["type"])
    platt = PlattCalibrator().fit(model.predict_proba(cal_rows[features])[:, 1], cal_rows.y.to_numpy())
    return model, platt


def _baseline(train, test):
    """Naive benchmark: touch rate by distance bucket only (what 'closer levels hit more' alone gives)."""
    bins = np.r_[0, 0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, np.inf]
    rate = train.groupby(pd.cut(train.abs_atr, bins), observed=False).y.mean()
    return pd.cut(test.abs_atr, bins).map(rate).astype(float).fillna(train.y.mean()).to_numpy()


def oos_path(root):
    """Walk-forward out-of-sample touch probability per (session, cutoff, level): feeds model backtests."""
    return DIR / f"{root}_{_key(root)}_oos.csv"


def study(root):
    """Walk-forward evaluation (annual refits from 2013), cached."""
    path = DIR / f"{root}_{_key(root)}_study.json"
    if path.exists() and oos_path(root).exists():
        return json.loads(path.read_text())
    from sklearn.metrics import roc_auc_score
    rows, _ = build(root)
    rows = rows.dropna(subset=["y"])
    no_conf = [f for f in FEATURES if not f.startswith("conf")]
    parts = []
    for year in range(2013, int(rows.year.max()) + 1):
        train, test = rows[rows.year < year], rows[rows.year == year]
        if train.session.nunique() < 500 or test.empty:
            continue
        m, pl = _fit(train, FEATURES)
        m2, pl2 = _fit(train, no_conf)
        parts.append(test.assign(p=pl.predict(m.predict_proba(test[FEATURES])[:, 1]), p_noconf=pl2.predict(m2.predict_proba(test[no_conf])[:, 1]),
                                 p_base=_baseline(train, test)))
    oos = pd.concat(parts, ignore_index=True)
    oos[["session", "year", "cutoff", "key", "price", "ref", "abs_atr", "p", "y"]].to_csv(oos_path(root), index=False)
    y = oos.y.to_numpy()
    brier = lambda p: round(float(np.mean((p - y) ** 2)), 4)
    report = {"root": root, "method": "annual walk-forward 2013-, train on earlier years only; Platt on last 15% of train sessions",
              "rows": int(len(oos)), "sessions": int(oos.session.nunique()), "base_rate": round(float(y.mean()), 3),
              "auc": round(float(roc_auc_score(y, oos.p)), 3), "auc_without_confluence": round(float(roc_auc_score(y, oos.p_noconf)), 3),
              "auc_distance_only": round(float(roc_auc_score(y, oos.p_base)), 3),
              "brier": brier(oos.p), "brier_without_confluence": brier(oos.p_noconf), "brier_distance_only": brier(oos.p_base)}
    calib = []
    for lo, hi in ((0, .1), (.1, .3), (.3, .5), (.5, .7), (.7, .9), (.9, .95), (.95, .99), (.99, 1.01)):
        g = oos[(oos.p >= lo) & (oos.p < hi)]
        if len(g):
            calib.append({"from": lo, "to": min(hi, 1.0), "n": int(len(g)), "predicted": round(float(g.p.mean()), 3),
                          "hit_rate": round(float(g.y.mean()), 3), "median_distance_atr": round(float(g.abs_atr.median()), 3)})
    report["calibration"] = calib
    far = oos[oos.abs_atr >= 0.25]  # levels at least a quarter-ATR away: the useful targets
    report["useful_targets"] = {"definition": "levels >= 0.25 ATR from price at the cutoff", "n": int(len(far)),
                                "base_rate": round(float(far.y.mean()), 3),
                                "p_over_70": {"n": int((far.p > .7).sum()), "hit_rate": round(float(far.y[far.p > .7].mean()), 3) if (far.p > .7).any() else None},
                                "p_over_80": {"n": int((far.p > .8).sum()), "hit_rate": round(float(far.y[far.p > .8].mean()), 3) if (far.p > .8).any() else None}}
    by_conf = oos.groupby(oos.conf_groups.clip(upper=4)).agg(n=("y", "size"), hit_rate=("y", "mean"), dist=("abs_atr", "median"))
    report["by_confluence_groups"] = {str(k): {"n": int(v.n), "hit_rate": round(float(v.hit_rate), 3), "median_distance_atr": round(float(v.dist), 3)}
                                      for k, v in by_conf.iterrows()}
    report["by_type"] = {sessions.LEVEL_NAMES[TYPES[int(t)]]: {"n": int(len(g)), "hit_rate": round(float(g.y.mean()), 3), "model_auc":
                         round(float(roc_auc_score(g.y, g.p)), 3) if g.y.nunique() > 1 else None, "median_distance_atr": round(float(g.abs_atr.median()), 3)}
                         for t, g in oos.groupby("type")}
    report["by_cutoff"] = {sessions.CUTOFF_LABEL[list(sessions.CUTOFFS)[int(c)]]: {"n": int(len(g)), "auc": round(float(roc_auc_score(g.y, g.p)), 3),
                           "brier": round(float(np.mean((g.p - g.y) ** 2)), 4)} for c, g in oos.groupby("cutoff")}
    report["direction_rest_of_day"] = _direction_study(root)
    DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2))
    return report


def _direction_study(root):
    """Does the intraday state at the cutoff predict the 16:00 close vs the cutoff price?"""
    _, state = build(root)
    state = state.assign(up=(state.close > state.price).astype(int))
    out = {}
    for name, g in state.groupby("cutoff_name"):
        res = {"sessions": int(len(g)), "close_above_cutoff_price": round(float(g.up.mean()), 3)}
        for label, mask in (("above VWAP", g.vs_vwap > 0), ("below VWAP", g.vs_vwap < 0), ("above VWAP +1σ", g.vs_vwap > 1), ("below VWAP −1σ", g.vs_vwap < -1)):
            if mask.sum() >= 50:
                res[label] = {"n": int(mask.sum()), "p_close_higher": round(float(g.up[mask].mean()), 3)}
        if g.orb.notna().any():
            for label in ("above", "below", "inside"):
                mask = g.orb == label
                if mask.sum() >= 50:
                    res[f"ORB {label}"] = {"n": int(mask.sum()), "p_close_higher": round(float(g.up[mask].mean()), 3)}
        out[sessions.CUTOFF_LABEL[name]] = res
    return out


def load_or_train(root):
    DIR.mkdir(parents=True, exist_ok=True)
    path = DIR / f"{root}_{_key(root)}.joblib"
    with FileLock(DIR / f"{root}.lock"):
        if path.exists():
            return joblib.load(path)
        rows, _ = build(root)
        rows = rows.dropna(subset=["y"])
        model, platt = _fit(rows, FEATURES)
        bundle = {"model": model, "platt": platt, "through": str(rows.session.max()), "rows": int(len(rows))}
        joblib.dump(bundle, path)
        return bundle


def score(root, frame):
    bundle = load_or_train(root)
    return bundle["platt"].predict(bundle["model"].predict_proba(frame[FEATURES])[:, 1])
