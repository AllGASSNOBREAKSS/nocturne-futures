"""Phase 3U pre-registered index-level experiment: do free macro/positioning/
filing features add out-of-sample information to Nasdaq-100 daily forecasts?

Scope: ^NDX cash index (research-grade Yahoo history), not NQ futures, not
order flow, not executable P&L. Every free-data value is joined by its
conservative ``available_at`` (merge-as-of, backward) against the feature
cutoff, so nothing published after the simulated prediction time is used.
The protocol is fixed before scoring; all C values are reported, none selected.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

from ..collector.store import Archive
from .daily_experiment import FEATURES as BASE, build_dataset

PROTOCOL = {
    "version": "phase3u-free-data-v1", "symbol": "^NDX",
    "test_years": list(range(2008, 2027)), "development_years": list(range(2008, 2024)),
    "exposed_years": [2024, 2025, 2026],
    "exposed_note": "2024+ was inspected by earlier phases with other features; scored once, never tuned on",
    "refit": "annual, expanding unless a window is given", "embargo_days": 5, "calibration_rows": 250,
    "primary_C": 0.2, "C_grid": [0.05, 0.2, 1.0], "windows_years": [5, 10, 20, None], "seed": 7,
    "quantiles": [0.5, 0.8, 0.9], "baseline_quantile_window": 250, "bootstrap": {"block": "calendar month", "reps": 2000},
    "lgbm": {"n_estimators": 300, "learning_rate": 0.03, "num_leaves": 15, "min_child_samples": 50,
             "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "random_state": 7, "verbose": -1},
    "verdict_rule": ("PASS only if the free-feature model improves Brier (direction) or mean pinball (range) "
                     "over BOTH the frequency/trailing baseline and the base-feature model with a 95% "
                     "block-bootstrap CI excluding zero in development years, and keeps the same sign in "
                     "exposed years; FAIL if the CI shows it is worse than the base model; otherwise INCONCLUSIVE."),
    "label_direction": "next observed session close greater than its open",
    "label_range": "next session (high - low) / feature-day close",
}

FRED_FEATURES = {"VIXCLS": 10, "VXNCLS": 10, "T10Y2Y": 10, "DGS10": 10, "BAA10Y": 10, "WALCL": 21, "DTWEXBGS": 21}
# Each source's own derived columns, computed on its observation sequence.
TRANSFORMS = {"VIXCLS": lambda v: {"vix": v, "vix_chg5": v - v.shift(5)},
              "VXNCLS": lambda v: {"vxn": v},
              "T10Y2Y": lambda v: {"t10y2y": v},
              "DGS10": lambda v: {"dgs10_chg5": v - v.shift(5)},
              "BAA10Y": lambda v: {"baa10y": v, "baa10y_chg20": v - v.shift(20)},
              "WALCL": lambda v: {"walcl_chg13": np.log(v / v.shift(13))},
              "DTWEXBGS": lambda v: {"usd_chg20": np.log(v / v.shift(20))}}
FREE = ["vix", "vix_chg5", "vxn_minus_vix", "t10y2y", "dgs10_chg5", "baa10y", "baa10y_chg20",
        "walcl_chg13", "usd_chg20", "cot_nq_am_net", "cot_nq_am_net_chg4", "cot_nq_lev_net",
        "cot_es_am_net", "megacap_filings_5d"]


def _asof(cutoffs: pd.Series, source: pd.DataFrame, columns, tolerance_days):
    left = pd.DataFrame({"cutoff": pd.to_datetime(cutoffs, utc=True).reset_index(drop=True),
                         "row": np.arange(len(cutoffs))}).sort_values("cutoff")
    right = source.sort_values("available_at")
    merged = pd.merge_asof(left, right[["available_at", *columns]], left_on="cutoff", right_on="available_at",
                           direction="backward", tolerance=pd.Timedelta(days=tolerance_days))
    return merged.sort_values("row").reset_index(drop=True)


def free_features(archive: Archive, cutoffs: pd.Series):
    """Point-in-time free features for each cutoff; returns (frame, lag_audit)."""
    out = pd.DataFrame(index=range(len(cutoffs)))
    audit = {}
    series = {}
    for name, tolerance in FRED_FEATURES.items():
        frame = archive.load("fred", name)
        if not frame.pit_eligible.all():
            raise ValueError(f"{name} is not PIT-eligible")
        frame["available_at"] = pd.to_datetime(frame.available_at, utc=True)
        frame = frame.sort_values("date").reset_index(drop=True)
        derived = TRANSFORMS[name](frame.value)
        frame = frame.assign(**derived)
        merged = _asof(cutoffs, frame, list(derived), tolerance)
        for column in derived:
            series[column] = merged[column]
        audit[name] = _lag(merged)
    out = out.assign(**series)
    out["vxn_minus_vix"] = out.pop("vxn") - out["vix"]

    cot = archive.load("cftc", "tff_futures_only")
    cot["available_at"] = pd.to_datetime(cot.available_at, utc=True)
    for code, prefix in (("209742", "cot_nq"), ("13874A", "cot_es")):
        market = cot[cot.cftc_contract_market_code.astype(str) == code].sort_values("report_date").reset_index(drop=True)
        oi = market.open_interest_all
        market[f"{prefix}_am_net"] = (market.asset_mgr_positions_long - market.asset_mgr_positions_short) / oi
        market[f"{prefix}_lev_net"] = (market.lev_money_positions_long - market.lev_money_positions_short) / oi
        market[f"{prefix}_am_net_chg4"] = market[f"{prefix}_am_net"] - market[f"{prefix}_am_net"].shift(4)
        columns = [f"{prefix}_am_net", f"{prefix}_lev_net", f"{prefix}_am_net_chg4"]
        merged = _asof(cutoffs, market, columns, 21)
        for column in columns:
            out[column] = merged[column]
        audit[f"CFTC_{code}"] = _lag(merged)
    out = out.drop(columns=["cot_es_lev_net", "cot_es_am_net_chg4"])

    sec = archive.load("sec", "megacap_filings")
    sec = sec[sec.form.isin(["10-K", "10-Q"])]
    times = np.sort(pd.to_datetime(sec.available_at, utc=True).to_numpy(dtype="datetime64[ns]"))
    cut = pd.to_datetime(cutoffs, utc=True).to_numpy(dtype="datetime64[ns]")
    out["megacap_filings_5d"] = np.searchsorted(times, cut, side="right") - \
        np.searchsorted(times, cut - np.timedelta64(5, "D"), side="right")
    audit["SEC_10K_10Q"] = {"rows": int(len(times)), "rule": "acceptance time <= cutoff, 5-day count"}
    return out[FREE], audit


def _lag(merged):
    lag = (merged.cutoff - merged.available_at).dt.total_seconds() / 86400
    return {"matched_fraction": round(float(merged.available_at.notna().mean()), 4),
            "median_lag_days": round(float(lag.median()), 3) if lag.notna().any() else None,
            "min_lag_days": round(float(lag.min()), 4) if lag.notna().any() else None}


def build(frame: pd.DataFrame, archive: Archive):
    data = build_dataset(frame, reserved_from="2100-01-01")
    bars = frame.sort_values("timestamp").reset_index(drop=True)
    complete = bars.source_complete.astype(str).str.lower().eq("true")
    close = bars.close.where(complete)
    extra = pd.DataFrame({"date": bars.date,
                          "range_next": ((bars.high - bars.low) / bars.close.where(complete)).shift(-1)
                          .where(complete.shift(-1, fill_value=False)) * 1.0,
                          "range_now": (bars.high - bars.low).where(complete) / close,
                          "trend_up": close > close.rolling(200).mean(),
                          "drawdown": close / close.rolling(252, min_periods=200).max() - 1})
    # Trailing empirical quantile of realized ranges up to the feature day (PIT).
    for q in PROTOCOL["quantiles"]:
        extra[f"trail_q{int(q * 100)}"] = extra.range_now.rolling(PROTOCOL["baseline_quantile_window"]).quantile(q)
    data = data.merge(extra, on="date", how="left", validate="one_to_one")
    features, audit = free_features(archive, data.feature_available_at.reset_index(drop=True))
    data = pd.concat([data.reset_index(drop=True), features], axis=1)
    data["year"] = pd.to_datetime(data.date).dt.year
    if (data.feature_available_at >= data.entry_time).any():
        raise ValueError("look-ahead: feature cutoff not before entry")
    return data, audit


def _splits(data, year, features, window):
    start = pd.Timestamp(f"{year}-01-01", tz="UTC")
    usable = data.dropna(subset=features + ["up", "range_next"])
    train = usable[usable.label_end < start - pd.Timedelta(days=PROTOCOL["embargo_days"])]
    if window:
        train = train[pd.to_datetime(train.date) >= pd.Timestamp(f"{year - window}-01-01")]
    return train


def run(data):
    from lightgbm import LGBMRegressor
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from ..ml.calibration import PlattCalibrator

    full = BASE + FREE
    test_mask = data[full + ["up", "range_next"]].notna().all(axis=1)
    configs = {f"base_C{c}_w{w or 'all'}": (BASE, c, w) for c in PROTOCOL["C_grid"] for w in PROTOCOL["windows_years"]}
    configs |= {f"free_C{c}_w{w or 'all'}": (full, c, w) for c in PROTOCOL["C_grid"] for w in (5, 10, None)}
    rows, folds = [], []
    for year in PROTOCOL["test_years"]:
        test = data[test_mask & (data.year == year)]
        if test.empty:
            continue
        record = test[["date", "year", "up", "next_return", "range_next", "vix", "trend_up", "drawdown"]
                      + [f"trail_q{int(q * 100)}" for q in PROTOCOL["quantiles"]]].copy()
        fold = {"year": year, "test_rows": len(test)}
        for name, (features, c, window) in configs.items():
            train = _splits(data, year, features, window)
            fit, calibration = train.iloc[:-PROTOCOL["calibration_rows"]], train.iloc[-PROTOCOL["calibration_rows"]:]
            model = make_pipeline(StandardScaler(), LogisticRegression(C=c, max_iter=2000, random_state=PROTOCOL["seed"]))
            model.fit(fit[features], fit.up)
            platt = PlattCalibrator().fit(model.predict_proba(calibration[features])[:, 1], calibration.up.to_numpy())
            record[f"p_{name}"] = platt.predict(model.predict_proba(test[features])[:, 1])
            fold[name] = {"train_rows": len(train), "train_start": str(train.date.min()), "train_end": str(train.date.max())}
        train = _splits(data, year, BASE, None)
        record["p_frequency"] = train.up.mean()
        for label, features in (("base", BASE), ("free", full)):
            train = _splits(data, year, features, None)
            for q in PROTOCOL["quantiles"]:
                model = LGBMRegressor(objective="quantile", alpha=q, **PROTOCOL["lgbm"])
                model.fit(train[features], train.range_next)
                record[f"lgbm_{label}_q{int(q * 100)}"] = model.predict(test[features])
        rows.append(record)
        folds.append(fold)
    return pd.concat(rows, ignore_index=True), folds


def direction_metrics(y, p):
    from sklearn.metrics import balanced_accuracy_score, roc_auc_score
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return {"n": int(len(y)), "auc": float(roc_auc_score(y, p)) if len(set(y)) > 1 else None,
            "balanced_accuracy": float(balanced_accuracy_score(y, p >= .5)),
            "brier": float(np.mean((p - y) ** 2)),
            "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p))),
            "mean_p": float(p.mean()), "base_rate": float(np.mean(y))}


def pinball(y, q, alpha):
    d = np.asarray(y) - np.asarray(q)
    return float(np.mean(np.maximum(alpha * d, (alpha - 1) * d)))


def range_metrics(frame, prefix):
    out = {}
    for q in PROTOCOL["quantiles"]:
        column = f"{prefix}_q{int(q * 100)}"
        out[f"q{int(q * 100)}"] = {"coverage": float((frame.range_next <= frame[column]).mean()),
                                   "pinball": pinball(frame.range_next, frame[column], q)}
    out["mean_pinball"] = float(np.mean([v["pinball"] for v in out.values()]))
    return out


def block_bootstrap(frame, loss_a, loss_b, reps, seed):
    """CI of mean(loss_a - loss_b), resampling calendar months."""
    diff = pd.Series(np.asarray(loss_a) - np.asarray(loss_b), index=frame.index)
    month = pd.to_datetime(frame.date).dt.to_period("M")
    groups = [diff[month == m].to_numpy() for m in month.unique()]
    rng = np.random.default_rng(seed)
    stats = [np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))]).mean() for _ in range(reps)]
    return {"mean": float(diff.mean()), "ci95": [float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5))]}


def strategy(frame, column, dead_zone=0.02):
    """Hypothetical next-session open-to-close index exposure; never NQ P&L."""
    position = np.where(frame[column] > .5 + dead_zone, 1, np.where(frame[column] < .5 - dead_zone, -1, 0))
    out = {}
    for bps in (0, 2, 5):
        gross = position * frame.next_return.to_numpy()
        net = np.where(position != 0, gross - bps / 1e4, 0.0)
        traded = net[position != 0]
        equity = np.cumprod(1 + net)
        wins, losses = traded[traded > 0], traded[traded <= 0]
        out[f"{bps}bps"] = {"trades": int(len(traded)), "exposure_fraction": float((position != 0).mean()),
                            "long_fraction": float((position == 1).mean()),
                            "win_rate": float((traded > 0).mean()) if len(traded) else None,
                            "net_expectancy_fraction": float(traded.mean()) if len(traded) else None,
                            "profit_factor": float(wins.sum() / -losses.sum()) if losses.sum() < 0 else None,
                            "total_return_fraction": float(equity[-1] - 1),
                            "max_drawdown_fraction": float(-(equity / np.maximum.accumulate(equity) - 1).min())}
    return out


def evaluate(predictions):
    reps, seed = PROTOCOL["bootstrap"]["reps"], PROTOCOL["seed"]
    prim = f"C{PROTOCOL['primary_C']}_wall"
    base_p, free_p = f"p_base_{prim}", f"p_free_{prim}"
    eras = {"development": predictions[predictions.year.isin(PROTOCOL["development_years"])],
            "exposed": predictions[predictions.year.isin(PROTOCOL["exposed_years"])],
            "all": predictions}
    models = ["p_frequency"] + [c for c in predictions.columns if c.startswith("p_") and c != "p_frequency"]
    report = {"direction": {}, "range": {}, "comparisons": {}, "by_year": {}, "regimes": {}, "strategy": {}}
    for era, frame in eras.items():
        y = frame.up.to_numpy()
        report["direction"][era] = {m: direction_metrics(y, frame[m]) for m in models}
        report["range"][era] = {"trailing_baseline": range_metrics(frame, "trail"),
                                "base_lgbm": range_metrics(frame, "lgbm_base"), "free_lgbm": range_metrics(frame, "lgbm_free")}
        sq = lambda col: (frame[col].to_numpy() - y) ** 2
        mean_pin = lambda prefix: np.mean([np.maximum(q * (frame.range_next - frame[f"{prefix}_q{int(q*100)}"]),
                                                      (q - 1) * (frame.range_next - frame[f"{prefix}_q{int(q*100)}"]))
                                           for q in PROTOCOL["quantiles"]], axis=0)
        report["comparisons"][era] = {
            "brier_free_minus_frequency": block_bootstrap(frame, sq(free_p), sq("p_frequency"), reps, seed),
            "brier_free_minus_base": block_bootstrap(frame, sq(free_p), sq(base_p), reps, seed),
            "brier_base_minus_frequency": block_bootstrap(frame, sq(base_p), sq("p_frequency"), reps, seed),
            "pinball_free_minus_trailing": block_bootstrap(frame, mean_pin("lgbm_free"), mean_pin("trail"), reps, seed),
            "pinball_free_minus_base": block_bootstrap(frame, mean_pin("lgbm_free"), mean_pin("lgbm_base"), reps, seed),
            "pinball_base_minus_trailing": block_bootstrap(frame, mean_pin("lgbm_base"), mean_pin("trail"), reps, seed)}
        report["strategy"][era] = {"free_primary": strategy(frame, free_p), "base_primary": strategy(frame, base_p),
                                   "always_long": strategy(frame.assign(always=1.0), "always")}
    for year, frame in predictions.groupby("year"):
        report["by_year"][str(year)] = {"n": len(frame),
                                        "direction": {m: direction_metrics(frame.up.to_numpy(), frame[m]) for m in ("p_frequency", base_p, free_p)},
                                        "range_mean_pinball": {"trailing": range_metrics(frame, "trail")["mean_pinball"],
                                                               "base": range_metrics(frame, "lgbm_base")["mean_pinball"],
                                                               "free": range_metrics(frame, "lgbm_free")["mean_pinball"]},
                                        "free_q80_coverage": float((frame.range_next <= frame.lgbm_free_q80).mean())}
    regimes = {"vix_lt15": predictions.vix < 15, "vix_15_25": predictions.vix.between(15, 25), "vix_gt25": predictions.vix > 25,
               "above_200d": predictions.trend_up.astype(bool), "below_200d": ~predictions.trend_up.astype(bool),
               "bear_drawdown_gt20pct": predictions.drawdown < -.2}
    for name, mask in regimes.items():
        frame = predictions[mask]
        report["regimes"][name] = {"n": int(len(frame)),
                                   "direction": {m: direction_metrics(frame.up.to_numpy(), frame[m]) for m in ("p_frequency", base_p, free_p)},
                                   "range_mean_pinball": {"trailing": range_metrics(frame, "trail")["mean_pinball"],
                                                          "base": range_metrics(frame, "lgbm_base")["mean_pinball"],
                                                          "free": range_metrics(frame, "lgbm_free")["mean_pinball"]}}
    report["verdicts"] = verdicts(report["comparisons"])
    return report


def verdicts(comparisons):
    def decide(vs_a, vs_b):
        dev_a, dev_b = comparisons["development"][vs_a], comparisons["development"][vs_b]
        exp_a, exp_b = comparisons["exposed"][vs_a], comparisons["exposed"][vs_b]
        if dev_b["ci95"][0] > 0:
            return "FAIL"
        if dev_a["ci95"][1] < 0 and dev_b["ci95"][1] < 0 and exp_a["mean"] < 0 and exp_b["mean"] < 0:
            return "PASS"
        return "INCONCLUSIVE"
    return {"direction_free_features": decide("brier_free_minus_frequency", "brier_free_minus_base"),
            "range_free_features": decide("pinball_free_minus_trailing", "pinball_free_minus_base")}


def fingerprint(archive: Archive, code: bytes, history_sha: str):
    parts = {"history_raw_sha256": history_sha, "code_sha256": hashlib.sha256(code).hexdigest(), "protocol": PROTOCOL}
    for source, dataset in [("fred", n) for n in FRED_FEATURES] + [("cftc", "tff_futures_only"), ("sec", "megacap_filings")]:
        parts[f"{source}/{dataset}"] = archive.latest(source, dataset)["normalized_sha256"]
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest(), parts
