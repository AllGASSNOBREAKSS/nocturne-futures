"""Decades-long next-day direction research on daily index history.

Expanding annual walk-forward with a two-year calibration block and a five-day
embargo. The final three years are reserved and never scored here.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score

from nocturne.adapters.yahoo_history import load_history
from nocturne.ml.calibration import PlattCalibrator, classification_metrics
from nocturne.research.validation import block_mean_interval

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data/history/yahoo_daily"

BASE = ["ret_1", "ret_5", "ret_20", "vol_20", "vol_ratio", "efficiency_20",
        "ma20_distance", "ma50_distance", "drawdown_60", "range_atr", "volume_z"]
GROUPS = {
    "volatility_context": ["vix_level", "vix_change_5", "vix_percentile"],
    "rates_context": ["tnx_level", "tnx_change_5", "tnx_change_20"],
    "cross_market": ["gspc_ret_5", "relative_5", "futures_relative_5"],
    "seasonality": ["weekday", "month", "turn_of_month"],
}
RESERVED_FROM = 2024


def build(symbol="^NDX"):
    frame = load_history(DAILY, symbol)
    frame["date"] = pd.to_datetime(frame.date)
    frame = frame.sort_values("date").reset_index(drop=True)
    close, high, low = frame.close.astype(float), frame.high.astype(float), frame.low.astype(float)
    returns = close.pct_change()
    volatility = returns.rolling(20).std()
    atr = (high - low).rolling(20).mean()
    path = close.diff().abs().rolling(20).sum()
    data = pd.DataFrame({
        "date": frame.date,
        "ret_1": returns / volatility,
        "ret_5": (close / close.shift(5) - 1) / (volatility * np.sqrt(5)),
        "ret_20": (close / close.shift(20) - 1) / (volatility * np.sqrt(20)),
        "vol_20": volatility / volatility.rolling(250).median(),
        "vol_ratio": volatility / volatility.rolling(250).mean(),
        "efficiency_20": (close - close.shift(20)).abs() / path,
        "ma20_distance": (close / close.rolling(20).mean() - 1) / volatility,
        "ma50_distance": (close / close.rolling(50).mean() - 1) / volatility,
        "drawdown_60": close / close.rolling(60).max() - 1,
        "range_atr": (high - low) / atr,
        "volume_z": (frame.volume - frame.volume.rolling(20).mean()) / frame.volume.rolling(20).std(),
        "weekday": frame.date.dt.dayofweek,
        "month": frame.date.dt.month,
        "turn_of_month": 0.0,
        "next_up": (returns.shift(-1) > 0).astype(float),
        "next_return": returns.shift(-1),
    })
    position = data.groupby([data.date.dt.year, data.date.dt.month]).cumcount()
    size = data.groupby([data.date.dt.year, data.date.dt.month]).date.transform("size")
    data["turn_of_month"] = ((position < 3) | (position >= size - 3)).astype(float)

    def context(symbol: str) -> pd.Series:
        series = load_history(DAILY, symbol).set_index("date").close
        series.index = pd.to_datetime(series.index)
        # Reindex to the target calendar, then restore the positional index so
        # column assignment aligns by position rather than by timestamp.
        return series.reindex(data.date).ffill().set_axis(data.index)

    vix = context("^VIX")
    data["vix_level"] = vix / vix.rolling(250).median()
    data["vix_change_5"] = vix.pct_change(5)
    data["vix_percentile"] = vix.rolling(250).apply(lambda s: (s <= s.iloc[-1]).mean(), raw=False)

    rates = context("^TNX")
    data["tnx_level"] = rates
    data["tnx_change_5"] = rates.diff(5)
    data["tnx_change_20"] = rates.diff(20)

    gspc = context("^GSPC")
    data["gspc_ret_5"] = gspc.pct_change(5)
    data["relative_5"] = (close.pct_change(5).to_numpy() - gspc.pct_change(5).to_numpy()) / volatility.to_numpy()

    futures = context("NQ=F")
    es = context("ES=F")
    data["futures_relative_5"] = (
        (futures.pct_change(5).to_numpy() - es.pct_change(5).to_numpy()) / volatility.to_numpy())
    return data


def fold(data, year):
    cutoff = pd.Timestamp(f"{year - 2}-01-01")
    embargo = pd.Timedelta(days=5)
    train = data[data.date < cutoff - embargo]
    cal = data[(data.date >= cutoff) & (data.date < pd.Timestamp(f"{year}-01-01") - embargo)]
    test = data[(data.date >= pd.Timestamp(f"{year}-01-01")) & (data.date < pd.Timestamp(f"{year + 1}-01-01"))]
    return train.dropna(subset=["next_up"]), cal.dropna(subset=["next_up"]), test.dropna(subset=["next_up"])


def main():
    data = build("^NDX")
    years = sorted(y for y in data.date.dt.year.unique() if 1990 <= y < RESERVED_FROM)
    variants = {"price_only": BASE, "all": BASE + sum(GROUPS.values(), [])}
    for group, columns in GROUPS.items():
        variants[f"price_plus_{group}"] = BASE + columns
    report = {"decision": "NO_PROMOTION", "holdout_scored": False,
              "instrument": "^NDX", "label": "next session close-to-close up",
              "walk_forward": {"type": "expanding annual", "calibration_years": 2,
                               "embargo_days": 5, "reserved_from": RESERVED_FROM,
                               "first_test_year": int(years[0]), "last_test_year": int(years[-1])},
              "variants": {}}
    for name, columns in variants.items():
        rows = []
        for year in years:
            train, cal, test = fold(data, year)
            if len(train) < 500 or len(cal) < 200 or len(test) < 100:
                continue
            if train.next_up.nunique() < 2 or cal.next_up.nunique() < 2:
                continue
            model = make_pipeline(SimpleImputer(), StandardScaler(),
                                  LogisticRegression(C=.2, max_iter=2000))
            model.fit(train[columns], train.next_up)
            raw_cal = model.predict_proba(cal[columns])[:, 1]
            raw_test = model.predict_proba(test[columns])[:, 1]
            probability = PlattCalibrator().fit(raw_cal, cal.next_up.to_numpy()).predict(raw_test)
            frequency = float(train.next_up.mean())
            frame = test[["date", "next_up"]].copy()
            frame["year"] = year
            frame["p_model"] = probability
            frame["p_frequency"] = frequency
            rows.append(frame)
        if not rows:
            continue
        predictions = pd.concat(rows, ignore_index=True)
        y = predictions.next_up.to_numpy()
        model_metrics = classification_metrics(y, predictions.p_model.to_numpy())
        model_metrics["auc"] = float(roc_auc_score(y, predictions.p_model))
        base_metrics = classification_metrics(y, predictions.p_frequency.to_numpy())
        base_metrics["auc"] = float(roc_auc_score(y, predictions.p_frequency))
        model_loss = (predictions.p_model - predictions.next_up) ** 2
        base_loss = (predictions.p_frequency - predictions.next_up) ** 2
        by_decade = {}
        for decade, group in predictions.groupby(predictions.year // 10 * 10):
            entry = classification_metrics(group.next_up.to_numpy(), group.p_model.to_numpy())
            entry["auc"] = float(roc_auc_score(group.next_up, group.p_model)) if group.next_up.nunique() == 2 else None
            by_decade[str(int(decade))] = entry
        report["variants"][name] = {
            "features": columns, "n": len(predictions),
            "model": model_metrics, "frequency": base_metrics,
            "brier_delta": block_mean_interval((model_loss - base_loss).to_numpy(),
                                               predictions.year.astype(str)),
            "by_decade": by_decade,
        }
        print(name, round(model_metrics["brier"], 5), round(base_metrics["brier"], 5),
              round(model_metrics["auc"], 4), len(predictions))
    (ROOT / "reports/phase3g_daily_direction.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
