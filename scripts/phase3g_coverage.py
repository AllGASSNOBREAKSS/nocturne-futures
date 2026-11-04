"""Historical coverage manifest and independent-source cross-checks."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

from nocturne.adapters.yahoo_history import DEFAULT_SYMBOLS, load_history

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data/history/yahoo_daily"


def integrity(frame: pd.DataFrame) -> dict:
    dates = pd.to_datetime(frame.date)
    gaps = dates.diff().dt.days.dropna()
    return {"rows": len(frame), "first": str(dates.min().date()), "last": str(dates.max().date()),
            "span_years": round((dates.max() - dates.min()).days / 365.25, 2),
            "duplicate_dates": int(dates.duplicated().sum()),
            "null_close": int(frame.close.isna().sum()),
            "nonpositive_close": int((frame.close <= 0).sum()),
            "zero_volume_rows": int((frame.volume == 0).sum()),
            "gaps_over_10_days": int((gaps > 10).sum()),
            "median_gap_days": float(gaps.median()) if len(gaps) else None}


def correlation(left: pd.DataFrame, right: pd.DataFrame, name: str) -> dict:
    a = left.set_index(pd.to_datetime(left.date)).close.pct_change()
    b = right.set_index(pd.to_datetime(right.date)).close.pct_change()
    joined = pd.concat([a, b], axis=1, join="inner").dropna()
    joined.columns = ["left", "right"]
    return {"pair": name, "overlap_days": len(joined),
            "return_correlation": round(float(joined.left.corr(joined.right)), 4),
            "first": str(joined.index.min().date()), "last": str(joined.index.max().date())}


def tnx_vs_fred(tnx: pd.DataFrame) -> dict | None:
    path = ROOT / "data/history/fred/normalized"
    candidates = sorted(path.glob("DGS10_*.csv"))
    if not candidates:
        return None
    fred = pd.read_csv(candidates[0])
    fred["date"] = pd.to_datetime(fred.date)
    series = tnx.copy()
    series["date"] = pd.to_datetime(series.date)
    joined = series.merge(fred, on="date", how="inner").dropna(subset=["close", "value"])
    if joined.empty:
        return None
    difference = joined.close - joined.value
    return {"pair": "TNX vs FRED DGS10", "overlap_days": len(joined),
            "mean_absolute_difference_pct_points": round(float(difference.abs().mean()), 4),
            "max_absolute_difference_pct_points": round(float(difference.abs().max()), 4),
            "note": "both quoted in percent; differences reflect timing and rounding"}


def main():
    frames = {}
    manifest = {"provider": "yahoo_public_unofficial", "datasets": {}, "cross_checks": [],
                "separation": {"index_levels": [], "etfs": [], "futures_proxies": [], "rates": []}}
    for symbol, meta in DEFAULT_SYMBOLS.items():
        try:
            frame = load_history(DAILY, symbol)
        except FileNotFoundError:
            manifest["datasets"][symbol] = {"status": "MISSING"}
            continue
        frames[symbol] = frame
        entry = {"name": meta["name"], "kind": meta["kind"], **integrity(frame)}
        manifest["datasets"][symbol] = entry
        bucket = {"index": "index_levels", "etf": "etfs", "futures_proxy": "futures_proxies",
                  "rate_index": "rates", "volatility_index": "index_levels"}[meta["kind"]]
        manifest["separation"][bucket].append(symbol)
    for a, b, label in (("^NDX", "QQQ", "NDX vs QQQ"), ("^GSPC", "SPY", "GSPC vs SPY"),
                        ("NQ=F", "ES=F", "NQ proxy vs ES proxy")):
        if a in frames and b in frames:
            manifest["cross_checks"].append(correlation(frames[a], frames[b], label))
    if "^TNX" in frames:
        check = tnx_vs_fred(frames["^TNX"])
        if check:
            manifest["cross_checks"].append(check)
    if "NQ=F" in frames:
        cached = pd.read_csv(ROOT / "data/market/daily/NQ.csv")
        manifest["cross_checks"].append(correlation(frames["NQ=F"], cached, "NQ proxy vs cached NQ daily"))
    manifest["notes"] = [
        "Index levels and ETFs are context, not tradable futures.",
        "Continuous futures proxies are unverified roll mappings and are never used as raw contracts.",
        "Availability is the next UTC midnight after the session date.",
    ]
    (ROOT / "reports/phase3g_coverage.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k: (v.get("rows"), v.get("first")) for k, v in manifest["datasets"].items()}, indent=1))
    print(json.dumps(manifest["cross_checks"], indent=1))


if __name__ == "__main__":
    main()
