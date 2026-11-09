"""One-click next-session prediction: levels, touch probabilities, regime, direction check.

Trained on authentic Databento sessions (2010 -> latest). Models:
- Upside/downside excursion from the last settle (ATR units): LightGBM quantile
  models at 8 levels, then conformal-corrected on the most recent 500 sessions
  (held out from fitting) so a stated 80% band really covers ~80%.
- Calibrated classifiers (Platt on the same held-out window) for the objectives
  Phase 4C validated: touch prior high / low / VWAP, expansion, compression.
- Direction is computed but always reported against its validation verdict
  (REJECT in Phase 4C): the UI shows "no edge" rather than a call.
Every issued prediction is appended to a journal once and scored later.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd

from ..shadow.locking import FileLock
from . import ROOT, STATE, dataset, indicators, market

DIR = STATE / "predictor"
QUANTILES = (0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.975)
CALIBRATION = 500
FEATURES = dataset.PRICE + dataset.INTRADAY + ["vix", "vix_chg5", "vxn_minus_vix"]
CLASSIFIERS = {"touch_prior_high": "lightgbm", "touch_prior_low": "logistic", "touch_prior_vwap": "lightgbm",
               "expansion": "logistic", "compression": "lightgbm", "direction": "logistic"}
VERSION = "predict-v1"


def _lgbm_quantile(alpha):
    from lightgbm import LGBMRegressor
    return LGBMRegressor(objective="quantile", alpha=alpha, n_estimators=300, learning_rate=0.03, num_leaves=15,
                         min_child_samples=50, subsample=0.8, subsample_freq=1, colsample_bytree=0.8, random_state=7, verbose=-1)


def _classifier(kind):
    if kind == "lightgbm":
        from lightgbm import LGBMClassifier
        return LGBMClassifier(n_estimators=200, learning_rate=0.03, num_leaves=15, min_child_samples=50, subsample=0.8,
                              subsample_freq=1, colsample_bytree=0.8, random_state=7, verbose=-1)
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    return make_pipeline(StandardScaler(), LogisticRegression(C=0.2, max_iter=2000))


def fit(train):
    """Fit all models on `train` (time-ordered); last CALIBRATION rows calibrate."""
    from ..ml.calibration import PlattCalibrator
    medians = train[FEATURES].median()
    X = train[FEATURES].fillna(medians)
    fit_rows, cal_rows = slice(None, -CALIBRATION), slice(-CALIBRATION, None)
    models = {"medians": medians, "excursion": {}, "classifiers": {}}
    for side in ("up", "dn"):
        y = train[f"{side}_exc_atr"]
        ok = y.notna().to_numpy()
        Xf, yf = X[fit_rows][ok[fit_rows]], y[fit_rows][ok[fit_rows]]
        Xc, yc = X[cal_rows][ok[cal_rows]], y[cal_rows][ok[cal_rows]]
        for q in QUANTILES:
            m = _lgbm_quantile(q).fit(Xf, yf)
            correction = float(np.quantile(yc.to_numpy() - m.predict(Xc), q))  # conformal: P(y <= pred + c) ~= q
            models["excursion"][(side, q)] = (m, correction)
    for name, kind in CLASSIFIERS.items():
        y = train[f"y_{name}"]
        ok = y.notna().to_numpy()
        Xf, yf = X[fit_rows][ok[fit_rows]], y[fit_rows][ok[fit_rows]]
        Xc, yc = X[cal_rows][ok[cal_rows]], y[cal_rows][ok[cal_rows]]
        m = _classifier(kind).fit(Xf, yf)
        platt = PlattCalibrator().fit(m.predict_proba(Xc)[:, 1], yc.to_numpy())
        models["classifiers"][name] = (m, platt, float(y[ok].tail(250).mean()))
    return models


def infer(models, rows):
    X = rows[FEATURES].fillna(models["medians"])
    out = {}
    for side in ("up", "dn"):
        grid = np.column_stack([m.predict(X) + c for q, (m, c) in sorted(((q, v) for (s, q), v in models["excursion"].items() if s == side))])
        out[side] = np.maximum.accumulate(np.maximum(grid, 0.0), axis=1)  # monotone, non-negative quantiles
    for name, (m, platt, base) in models["classifiers"].items():
        out[name] = platt.predict(m.predict_proba(X)[:, 1])
        out[f"{name}_base"] = base
    return out


def exceed_probability(quantiles, distance):
    """P(excursion >= distance) by interpolating the predicted quantile grid."""
    qs = np.array(QUANTILES)
    if distance <= quantiles[0]:
        return {"p": float(1 - qs[0] * distance / quantiles[0]) if quantiles[0] > 0 else 1.0, "bound": ">95%"} if distance > 0 else {"p": 1.0, "bound": None}
    if distance >= quantiles[-1]:
        return {"p": float(1 - qs[-1]), "bound": "<2.5%"}
    return {"p": float(1 - np.interp(distance, quantiles, qs)), "bound": None}


def _key(root):
    manifest = json.loads((market.DATABENTO / "manifest.json").read_text())
    vix = market.archive().latest("fred", "VIXCLS")
    return hashlib.sha256(f"{VERSION}|{manifest[root + '_1d']['sha256']}|{manifest[root + '_5m']['sha256']}|{vix['normalized_sha256'] if vix else ''}".encode()).hexdigest()[:16]


def load_or_train(root):
    DIR.mkdir(parents=True, exist_ok=True)
    path = DIR / f"{root}_{_key(root)}.joblib"
    with FileLock(DIR / f"{root}.lock"):
        if path.exists():
            return joblib.load(path)
        data, _ = dataset.build(root, "databento")
        train = data.dropna(subset=["up_exc_atr", "dn_exc_atr"])
        bundle = {"models": fit(train), "trained_at": datetime.now(timezone.utc).isoformat(), "rows": int(len(train)),
                  "through": train.date.iloc[-1], "key": path.stem}
        joblib.dump(bundle, path)
        return bundle


def _verdicts(root):
    path = ROOT / "reports/phase4c_ml.json"
    if not path.exists():
        return {}
    rows = [r for r in json.loads(path.read_text())["rows"] if r["root"] == root and r["group"] == "main"]
    out = {}
    for r in rows:
        name = r["objective"]
        if name in CLASSIFIERS:
            rank = {"ACCEPT_RESEARCH_ONLY": 2, "INCONCLUSIVE": 1, "REJECT": 0}.get(r["verdict"], 0)
            out[name] = max(out.get(name, "REJECT"), r["verdict"], key=lambda v: {"ACCEPT_RESEARCH_ONLY": 2, "INCONCLUSIVE": 1, "REJECT": 0}[v]) if rank else out.get(name, r["verdict"])
    return out


def _latest_row(root):
    """Newest complete session: Databento, or free Yahoo bars when they are newer."""
    db, _ = dataset.build(root, "databento")
    try:
        yh, _ = dataset.build(root, "yahoo")
    except ValueError:
        yh = None
    if yh is not None and len(yh) and yh.date.iloc[-1] > db.date.iloc[-1]:
        return yh.iloc[[-1]], "yahoo", "Yahoo continuous futures (free, delayed); models trained on Databento"
    return db.iloc[[-1]], "databento", "Databento GLBX.MDP3 contract bars"


def _next_session(date):
    d = pd.Timestamp(date) + pd.Timedelta(days=1)
    while d.weekday() >= 5:
        d += pd.Timedelta(days=1)
    return str(d.date())


def predict(root):
    bundle = load_or_train(root)
    row, source, source_label = _latest_row(root)
    out = infer(bundle["models"], row)
    close, atr = float(row.close.iloc[0]), float(row.atr20_pts.iloc[0])
    up_q, dn_q = out["up"][0], out["dn"][0]
    pts = lambda v: round(v * atr, 2)
    projected = {"high": {f"p{int(q * 100)}": round(close + pts(v), 2) for q, v in zip(QUANTILES, up_q)},
                 "low": {f"p{int(q * 100)}": round(close - pts(v), 2) for q, v in zip(QUANTILES, dn_q)}}
    expected_range = {"p50": float(round(pts(up_q[3]) + pts(dn_q[3]), 1)), "p80_high": float(projected["high"]["p90"]), "p80_low": float(projected["low"]["p90"])}
    verdicts = _verdicts(root)
    levels = []

    def add(name, price, kind, basis, model=None):
        if price is None or not np.isfinite(price):
            return
        distance = float(price) - close
        p = exceed_probability(up_q if distance >= 0 else dn_q, abs(distance) / atr)
        entry = {"name": name, "price": round(float(price), 2), "kind": kind, "basis": basis, "distance_points": round(distance, 2),
                 "side": "above" if distance >= 0 else "below", "touch_probability": round(p["p"], 3), "bound": p["bound"],
                 "method": "excursion distribution"}
        if model and verdicts.get(model) == "ACCEPT_RESEARCH_ONLY":
            entry.update(touch_probability=round(float(out[model][0]), 3), bound=None, method=f"validated classifier ({model})",
                         base_rate=round(out[f"{model}_base"], 3))
        levels.append(entry)

    r0 = row.iloc[0]
    add("Prior session high", r0.prior_high, "reference", "last completed Globex session", "touch_prior_high")
    add("Prior session low", r0.prior_low, "reference", "last completed Globex session", "touch_prior_low")
    add("Prior session VWAP", r0.prior_vwap, "auction", "volume-weighted, last session", "touch_prior_vwap")
    add("Overnight high", r0.lvl_on_high, "session", "18:00-09:30 ET")
    add("Overnight low", r0.lvl_on_low, "session", "18:00-09:30 ET")
    add("RTH high", r0.lvl_rth_high, "session", "09:30-16:00 ET")
    add("RTH low", r0.lvl_rth_low, "session", "09:30-16:00 ET")
    add("Initial balance high", r0.lvl_ib_high, "session", "first RTH hour")
    add("Initial balance low", r0.lvl_ib_low, "session", "first RTH hour")
    daily_ref, _ = market.bars(root, "1d", limit=30, source=source)
    daily_ref = daily_ref[daily_ref.timestamp.dt.tz_convert("America/New_York").dt.date.astype(str) <= str(r0.date)]
    add("5-session high", daily_ref.high.tail(5).max(), "reference", "daily")
    add("5-session low", daily_ref.low.tail(5).min(), "reference", "daily")
    add("20-session high", daily_ref.high.tail(20).max(), "reference", "daily")
    add("20-session low", daily_ref.low.tail(20).min(), "reference", "daily")
    try:
        from ..auction.volume_profile import build_bar_approximation
        from ..instruments import get_instrument
        five, _ = market.bars(root, "5m", limit=400, source=source)
        session = five[indicators.globex_session(five.timestamp).astype(str) == str(r0.date)]
        prof = build_bar_approximation(session.assign(available_at=session.timestamp + pd.Timedelta(minutes=5)), root,
                                       get_instrument(root).tick_size, session_type="ETH", bin_ticks=8 if root == "NQ" else 2)
        add("POC", prof.poc_price, "auction", "volume profile (bar approximation)")
        add("Value area high", prof.vah_price, "auction", "volume profile (bar approximation)")
        add("Value area low", prof.val_price, "auction", "volume profile (bar approximation)")
    except (ValueError, KeyError):
        pass
    for label, side, q in (("Upside 50%", "above", 0.5), ("Upside 25%", "above", 0.75), ("Upside 10%", "above", 0.9),
                           ("Downside 50%", "below", 0.5), ("Downside 25%", "below", 0.75), ("Downside 10%", "below", 0.9)):
        price = projected["high" if side == "above" else "low"][f"p{int(q * 100)}"]
        levels.append({"name": label, "price": price, "kind": "projection", "basis": "calibrated excursion quantile",
                       "distance_points": round(price - close, 2), "side": side, "touch_probability": round(1 - q, 3), "bound": None,
                       "method": "excursion distribution"})
    # One row per price: confluent levels are merged; a validated classifier's probability wins.
    merged = {}
    for item in levels:
        key = round(item["price"] / 0.25) * 0.25
        if key not in merged:
            merged[key] = {**item, "names": [item["name"]]}
            continue
        keep = merged[key]
        keep["names"].append(item["name"])
        if item["method"].startswith("validated") and not keep["method"].startswith("validated"):
            keep.update({k: item[k] for k in ("touch_probability", "bound", "method", "kind", "basis")}, base_rate=item.get("base_rate"))
    levels = []
    for item in merged.values():
        item["confluence"] = len(item["names"])
        item["name"] = " · ".join(dict.fromkeys(item["names"]))
        levels.append(item)
    levels.sort(key=lambda x: -x["price"])
    daily, _ = market.bars(root, "1d", limit=400, source=source)
    snapshot = {"rsi14": round(float(indicators.rsi(daily.close, 14).iloc[-1]), 1), "adx14": round(float(indicators.adx(daily, 14).iloc[-1]), 1),
                "atr20": round(atr, 1), "close_vs_sma50": round(float(daily.close.iloc[-1] / indicators.sma(daily.close, 50).iloc[-1] - 1) * 100, 2),
                "close_vs_sma200": round(float(daily.close.iloc[-1] / indicators.sma(daily.close, 200).iloc[-1] - 1) * 100, 2),
                "vix": None if pd.isna(row.vix.iloc[0]) else round(float(row.vix.iloc[0]), 2),
                "close_location": round(float(row.close_location.iloc[0]), 2), "last_range_atr": round(float(row.range_atr.iloc[0]), 2)}
    drivers = _drivers(bundle["models"], row)
    regime = {name: {"probability": round(float(out[name][0]), 3), "base_rate": round(out[f"{name}_base"], 3), "verdict": verdicts.get(name)}
              for name in ("expansion", "compression")}
    direction = {"p_up": round(float(out["direction"][0]), 3), "base_rate": round(out["direction_base"], 3), "verdict": verdicts.get("direction", "REJECT"),
                 "message": "No edge: next-session direction failed independent validation for NQ and ES. Treat as a coin flip."}
    signals = json.loads((ROOT / "reports/phase4c_signals.json").read_text()) if (ROOT / "reports/phase4c_signals.json").exists() else {}
    record = {"root": root, "model_version": VERSION, "model_key": bundle["key"], "trained_through": bundle["through"],
              "data_through": row.date.iloc[0], "target_session": _next_session(row.date.iloc[0]), "source": source,
              "source_label": source_label, "reference_close": close, "atr20": round(atr, 2),
              "expected_range_points": expected_range, "projected": projected, "levels": levels, "regime": regime,
              "direction": direction, "indicators": snapshot, "drivers": drivers,
              "strategies": {"candidates": signals.get("candidates"), "accepted": signals.get("accepted"),
                             "message": "No strategy or signal passed independent validation; no trade signal is produced."},
              "track_record": track_record(root), "trading_decision": "NO_TRADE"}
    record["journal"] = journal(record)
    return record


def _drivers(models, row):
    X = row[FEATURES].fillna(models["medians"])
    out = []
    for name in ("expansion", "touch_prior_high"):
        m = models["classifiers"][name][0]
        if hasattr(m, "booster_"):
            contrib = m.predict(X, pred_contrib=True)[0][:-1]
        else:
            scaler, logit = m.steps[0][1], m.steps[-1][1]
            contrib = logit.coef_[0] * scaler.transform(X)[0]
        top = np.argsort(-np.abs(contrib))[:4]
        out.append({"model": name, "top": [{"feature": FEATURES[i], "value": None if pd.isna(row[FEATURES[i]].iloc[0]) else round(float(row[FEATURES[i]].iloc[0]), 4),
                                            "effect": "raises" if contrib[i] > 0 else "lowers"} for i in top]})
    return out


def track_record(root):
    """Walk-forward accuracy of this exact method (annual refits 2013-2026), cached."""
    DIR.mkdir(parents=True, exist_ok=True)
    path = DIR / f"{root}_{_key(root)}_track.json"
    if path.exists():
        return json.loads(path.read_text())
    data, _ = dataset.build(root, "databento")
    data = data.dropna(subset=["up_exc_atr", "dn_exc_atr"]).reset_index(drop=True)
    rows = []
    for year in range(2013, 2027):
        train = data[pd.to_datetime(data.date) < pd.Timestamp(f"{year}-01-01") - pd.Timedelta(days=5)]
        test = data[data.year == year]
        if len(train) < 1000 or test.empty:
            continue
        out = infer(fit(train), test)
        frame = pd.DataFrame({"year": year, "up": test.up_exc_atr.to_numpy(), "dn": test.dn_exc_atr.to_numpy()})
        for k, q in enumerate(QUANTILES):
            frame[f"up_q{q}"], frame[f"dn_q{q}"] = out["up"][:, k], out["dn"][:, k]
        for name in ("touch_prior_high", "touch_prior_low", "touch_prior_vwap", "expansion", "compression"):
            frame[f"p_{name}"], frame[f"y_{name}"] = out[name], test[f"y_{name}"].to_numpy()
            frame[f"b_{name}"] = test[f"base_{name}"].to_numpy()
        rows.append(frame)
    f = pd.concat(rows, ignore_index=True)
    record = {"method": "annual walk-forward 2013-2026, same models and conformal correction", "sessions": int(len(f)),
              "coverage": {side: {f"p{int(q * 100)}": round(float((f[side] <= f[f"{side}_q{q}"]).mean()), 3) for q in QUANTILES} for side in ("up", "dn")},
              "classifiers": {}, "by_year_high_p75_reached": {}}
    for name in ("touch_prior_high", "touch_prior_low", "touch_prior_vwap", "expansion", "compression"):
        g = f.dropna(subset=[f"y_{name}", f"b_{name}"])
        y, p, b = g[f"y_{name}"].to_numpy(), g[f"p_{name}"].to_numpy(), g[f"b_{name}"].to_numpy()
        from sklearn.metrics import roc_auc_score
        record["classifiers"][name] = {"n": int(len(g)), "brier": round(float(np.mean((p - y) ** 2)), 4), "baseline_brier": round(float(np.mean((b - y) ** 2)), 4),
                                       "auc": round(float(roc_auc_score(y, p)), 3), "hit_rate_when_p_over_70": round(float(y[p > 0.7].mean()), 3) if (p > 0.7).any() else None,
                                       "n_p_over_70": int((p > 0.7).sum())}
    for year, g in f.groupby("year"):
        record["by_year_high_p75_reached"][str(year)] = round(float((g.up >= g["up_q0.25"]).mean()), 3)
    path.write_text(json.dumps(record, indent=2))
    return record


def journal(record):
    """Append each (root, target session) prediction once; score earlier ones whose session completed."""
    DIR.mkdir(parents=True, exist_ok=True)
    path, outcomes = DIR / f"{record['root']}_journal.jsonl", DIR / f"{record['root']}_outcomes.jsonl"
    with FileLock(DIR / f"{record['root']}_journal.lock"):
        issued = [json.loads(x) for x in path.read_text().splitlines()] if path.exists() else []
        scored = {json.loads(x)["prediction_id"] for x in outcomes.read_text().splitlines()} if outcomes.exists() else set()
        pid = hashlib.sha256(f"{record['root']}|{record['target_session']}|{record['model_version']}".encode()).hexdigest()[:20]
        if pid not in {p["prediction_id"] for p in issued}:
            entry = {"prediction_id": pid, "issued_at": datetime.now(timezone.utc).isoformat(),
                     **{k: record[k] for k in ("root", "target_session", "data_through", "source", "model_version", "model_key", "reference_close",
                                               "atr20", "projected", "regime", "direction")},
                     "levels": [{k: l[k] for k in ("name", "price", "touch_probability")} for l in record["levels"]]}
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(entry, sort_keys=True) + "\n")
            issued.append(entry)
        for source in ("databento", "yahoo"):
            try:
                daily, _ = market.bars(record["root"], "1d", limit=60, source=source)
            except ValueError:
                continue
            sessions = {str(pd.Timestamp(t).tz_convert("America/New_York").date()): (h, l) for t, h, l in zip(daily.timestamp, daily.high, daily.low)}
            for p in issued:
                if p["prediction_id"] in scored or p["target_session"] not in sessions:
                    continue
                high, low = sessions[p["target_session"]]
                touched = [{"name": l["name"], "price": l["price"], "p": l["touch_probability"], "touched": bool(low <= l["price"] <= high)} for l in p["levels"]]
                result = {"prediction_id": p["prediction_id"], "evaluated_at": datetime.now(timezone.utc).isoformat(), "source": source,
                          "realized_high": float(high), "realized_low": float(low),
                          "high_within_p10_p90": bool(p["projected"]["high"]["p10"] <= high <= p["projected"]["high"]["p90"]),
                          "low_within_p10_p90": bool(p["projected"]["low"]["p90"] <= low <= p["projected"]["low"]["p10"]),
                          "levels": touched, "brier_levels": round(float(np.mean([(l["p"] - l["touched"]) ** 2 for l in touched])), 4)}
                with outcomes.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(result, sort_keys=True) + "\n")
                scored.add(p["prediction_id"])
        results = [json.loads(x) for x in outcomes.read_text().splitlines()] if outcomes.exists() else []
    return {"issued": len(issued), "evaluated": len(results),
            "high_band_hit_rate": round(float(np.mean([r["high_within_p10_p90"] for r in results])), 3) if results else None,
            "low_band_hit_rate": round(float(np.mean([r["low_within_p10_p90"] for r in results])), 3) if results else None,
            "recent": results[-5:]}
