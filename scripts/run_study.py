#!/usr/bin/env python
"""Rebuild the 15-year base-rate study.

Usage:
    python scripts/run_study.py                  # use committed CSVs
    python scripts/run_study.py --fetch          # refresh CSVs from Yahoo
    python scripts/run_study.py --cache <dir>    # import Yahoo chart JSON dumps

The output is data/studies/fomc_2024_2026.json, the file the report reads.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocturne.stats import all_days, event_stats, seasonality  # noqa: E402

CODES = {"ES": "ES=F", "NQ": "NQ=F", "GC": "GC=F", "SI": "SI=F", "VIX": "^VIX"}
CSV_DIR = ROOT / "data" / "studies" / "daily_15y"
OUT = ROOT / "data" / "studies" / "fomc_2024_2026.json"

# Decision days, verified against the Federal Reserve FOMC calendar.
FOMC = [
    "2024-01-31", "2024-03-20", "2024-05-01", "2024-06-12",
    "2024-07-31", "2024-09-18", "2024-11-07", "2024-12-18",
    "2025-01-29", "2025-03-19", "2025-05-07", "2025-06-18",
    "2025-07-30", "2025-09-17", "2025-10-29", "2025-12-10",
    "2026-01-28", "2026-03-18", "2026-04-29", "2026-06-17",
    "2026-07-29", "2026-09-16",
]


def frame_from_rows(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df[["date", "open", "high", "low", "close"]].sort_values("date").reset_index(drop=True)


def load_csv(code: str) -> pd.DataFrame:
    path = CSV_DIR / f"{code}.csv"
    if not path.exists():
        raise FileNotFoundError(f"{path} missing; run with --fetch or --cache")
    return frame_from_rows(pd.read_csv(path).to_dict("records"))


def import_cache(code: str, cache_dir: Path) -> pd.DataFrame:
    symbol = CODES[code]
    name = symbol.replace("^", "").replace("=", "") + ".json"
    path = cache_dir / name
    if not path.exists():
        raise FileNotFoundError(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    rows = []
    for i, timestamp in enumerate(result["timestamp"]):
        if quote["close"][i] is None:
            continue
        rows.append(
            {
                "date": pd.to_datetime(timestamp, unit="s").strftime("%Y-%m-%d"),
                "open": quote["open"][i],
                "high": quote["high"][i],
                "low": quote["low"][i],
                "close": quote["close"][i],
            }
        )
    return frame_from_rows(rows)


def fetch(code: str) -> pd.DataFrame:
    import requests

    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{CODES[code]}?range=15y&interval=1d"
    response = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0"},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    rows = []
    for i, timestamp in enumerate(result["timestamp"]):
        if quote["close"][i] is None:
            continue
        rows.append(
            {
                "date": pd.to_datetime(timestamp, unit="s").strftime("%Y-%m-%d"),
                "open": quote["open"][i],
                "high": quote["high"][i],
                "low": quote["low"][i],
                "close": quote["close"][i],
            }
        )
    return frame_from_rows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true", help="refresh CSVs from Yahoo")
    parser.add_argument("--cache", type=Path, help="directory of Yahoo chart JSON dumps")
    parser.add_argument(
        "--as-of",
        default="2026-10-27",
        help="exclude bars after this date (default: the published call date)",
    )
    args = parser.parse_args()

    CSV_DIR.mkdir(parents=True, exist_ok=True)
    frames: dict[str, pd.DataFrame] = {}

    for code in CODES:
        if args.cache:
            df = import_cache(code, args.cache)
            df.to_csv(CSV_DIR / f"{code}.csv", index=False)
        elif args.fetch:
            df = fetch(code)
            df.to_csv(CSV_DIR / f"{code}.csv", index=False)
        else:
            df = load_csv(code)
        frames[code] = df[df["date"] <= args.as_of].reset_index(drop=True)

    instruments = {code: frames[code] for code in ("ES", "NQ", "GC", "SI")}
    windows = {
        "all": {
            "label": "All days (15y)",
            "n": int(len(instruments["ES"])),
            "instruments": {code: all_days(df) for code, df in instruments.items()},
        },
        "fomc_2024_2026": {
            "label": "FOMC decision days (2024–26)",
            "n": len(FOMC),
            "instruments": {code: event_stats(df, FOMC) for code, df in instruments.items()},
        },
        "oct28": {
            "label": "Oct 28 (15y)",
            "n": int(instruments["ES"]["date"].str[5:].eq("10-28").sum()),
            "instruments": {code: seasonality(df, "10-28") for code, df in instruments.items()},
        },
    }

    payload = {
        "generated_at": "2026-10-27",
        "source": "Yahoo Finance daily bars, 15 years",
        "windows": windows,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    print(f"wrote {OUT.relative_to(ROOT)}")
    for key, window in windows.items():
        cells = " | ".join(
            f"{code} {window['instruments'][code]['avg_ret']:+.2f}% "
            f"({window['instruments'][code]['pct_up']:.0f}% up)"
            for code in instruments
        )
        print(f"{key:16s} n={window['n']:<5} {cells}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
