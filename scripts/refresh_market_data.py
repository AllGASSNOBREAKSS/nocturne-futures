#!/usr/bin/env python
"""Refresh the backend daily market store.

The 15-year study CSVs are frozen research artifacts. The backend reads
`data/market/daily/<CODE>.csv`, which can be refreshed independently.

Default mode appends the committed bridge bars for 2026-10-29, 2026-10-30 and
2026-11-02 (Yahoo daily bars). `--fetch` pulls a fresh 2-year daily history from
Yahoo instead.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocturne.adapters.yahoo import bars_frame, fetch_events  # noqa: E402

STUDY = ROOT / "data" / "studies" / "daily_15y"
MARKET = ROOT / "data" / "market" / "daily"
CODES = {"NQ": "NQ=F", "ES": "ES=F", "GC": "GC=F", "SI": "SI=F", "VIX": "^VIX"}

BRIDGE = {
    "ES": [
        ("2026-10-29", 7767.75, 7773.75, 7709.50, 7754.25),
        ("2026-10-30", 7709.25, 7713.00, 7558.25, 7614.00),
        ("2026-11-02", 7626.00, 7693.75, 7570.75, 7582.25),
    ],
    "NQ": [
        ("2026-10-29", 29793.50, 29794.25, 29111.00, 29562.00),
        ("2026-10-30", 29180.00, 29180.00, 28232.75, 28534.00),
        ("2026-11-02", 28587.75, 28891.25, 28101.75, 28210.50),
    ],
    "GC": [
        ("2026-10-29", 4081.40, 4081.70, 4016.30, 4031.40),
        ("2026-10-30", 4033.60, 4038.20, 3879.30, 3898.90),
        ("2026-11-02", 3890.00, 3980.80, 3889.00, 3956.90),
    ],
    "SI": [
        ("2026-10-29", 53.22, 53.22, 51.85, 52.19),
        ("2026-10-30", 51.84, 51.84, 48.88, 49.10),
        ("2026-11-02", 49.20, 51.34, 49.09, 50.61),
    ],
    "VIX": [
        ("2026-10-28", 17.47, 17.77, 16.21, 16.91),
        ("2026-10-29", 17.15, 17.36, 16.21, 17.20),
        ("2026-10-30", 18.43, 23.93, 18.03, 19.42),
        ("2026-11-02", 19.05, 21.77, 18.03, 21.41),
    ],
}


def append_bridge(code: str) -> pd.DataFrame:
    frame = pd.read_csv(STUDY / f"{code}.csv")
    frame["date"] = pd.to_datetime(frame["date"]).dt.strftime("%Y-%m-%d")
    existing = set(frame["date"])
    additions = [
        {"date": date, "open": open_, "high": high, "low": low, "close": close}
        for date, open_, high, low, close in BRIDGE[code]
        if date not in existing
    ]
    if additions:
        frame = pd.concat([frame, pd.DataFrame(additions)], ignore_index=True)
    return frame.sort_values("date").reset_index(drop=True)


def fetch(code: str) -> pd.DataFrame:
    events = fetch_events(CODES[code], range_="2y", interval="1d")
    frame = bars_frame(events)
    frame["date"] = pd.to_datetime(frame["timestamp"], utc=True).dt.strftime("%Y-%m-%d")
    return frame[["date", "open", "high", "low", "close"]].sort_values("date").reset_index(drop=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    args = parser.parse_args()

    MARKET.mkdir(parents=True, exist_ok=True)
    for code in CODES:
        frame = fetch(code) if args.fetch else append_bridge(code)
        out = MARKET / f"{code}.csv"
        frame.to_csv(out, index=False)
        print(f"{code}: {len(frame)} rows -> {out.relative_to(ROOT)} (last {frame['date'].iloc[-1]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
