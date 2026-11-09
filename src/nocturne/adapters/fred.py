"""Official FRED CSV context snapshots; current vintages are NOT PIT features.

Date is an observation date, not a publication timestamp. These data must not
be joined to historical features without a separate release/vintage history.
"""
import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import requests

SERIES = {"DGS10": "Federal Reserve H.15 10-year Treasury yield",
          "DGS2": "Federal Reserve H.15 2-year Treasury yield",
          "DFF": "Federal Reserve effective federal funds rate",
          "CPIAUCSL": "BLS CPI (seasonally adjusted, revisable)",
          "UNRATE": "BLS unemployment (seasonally adjusted, revisable)",
          "NASDAQ100": "Nasdaq-100 closing index via FRED; Nasdaq-origin distributor check, not independent upstream data",
          # Phase 3U free-data expansion (daily market series are rarely revised;
          # monthly/weekly macro series remain revisable context, not PIT features).
          "VIXCLS": "CBOE VIX close",
          "VXNCLS": "CBOE Nasdaq-100 volatility index close",
          "T10Y2Y": "10-year minus 2-year Treasury constant-maturity spread (H.15-derived)",
          "T10YIE": "10-year breakeven inflation (H.15-derived)",
          "BAA10Y": "Moody's Baa corporate yield minus 10-year Treasury",
          "DTWEXBGS": "Broad trade-weighted US dollar index (H.10, weekly release)",
          "WALCL": "Federal Reserve total assets (H.4.1, weekly Wednesday level)",
          "RRPONTSYD": "Overnight reverse repurchase agreements (NY Fed)",
          "NFCI": "Chicago Fed National Financial Conditions Index (weekly, revisable)",
          "USREC": "NBER recession indicator (assigned retrospectively; never a PIT feature)"}


def parse_series(payload: bytes, series: str):
    if series not in SERIES:
        raise ValueError("series not approved in context inventory")
    frame = pd.read_csv(io.BytesIO(payload))
    time = "observation_date" if "observation_date" in frame else "DATE"
    if time not in frame or series not in frame:
        raise ValueError("unexpected FRED CSV schema")
    out = pd.DataFrame({"date": pd.to_datetime(frame[time], errors="raise"),
                        "value": pd.to_numeric(frame[series], errors="coerce")})
    if out.date.duplicated().any():
        raise ValueError("duplicate FRED dates")
    return out.sort_values("date")


def fetch_context(series: str, root: Path, start="1986-01-01", end="2026-11-03"):
    if series not in SERIES:
        raise ValueError("unknown series")
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    response = requests.get(url, params={"id": series, "cosd": start, "coed": end}, timeout=45)
    response.raise_for_status()
    frame = parse_series(response.content, series)
    frame = frame[(frame.date >= pd.Timestamp(start)) & (frame.date <= pd.Timestamp(end))]
    if frame.value.notna().sum() == 0:
        raise ValueError("empty FRED observations")
    digest = hashlib.sha256(response.content).hexdigest()
    root = Path(root)
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "normalized").mkdir(exist_ok=True)
    (root / "raw" / f"{series}_{digest}.csv").write_bytes(response.content)
    normalized = root / "normalized" / f"{series}_{digest}.csv"
    frame.to_csv(normalized, index=False)
    metadata = {"series": series, "description": SERIES[series], "source": response.url,
                "sha256": digest, "normalized_sha256": hashlib.sha256(normalized.read_bytes()).hexdigest(),
                "rows": len(frame), "observations": int(frame.value.notna().sum()),
                "first": str(frame.date.min().date()), "last": str(frame.date.max().date()),
                "received_at": pd.Timestamp.now(tz="UTC").isoformat(),
                "vintage": "latest_at_download", "historical_feature_eligible": False,
                "consensus_available": False, "publication_times_available": False}
    (root / f"{series}_{digest}.json").write_text(json.dumps(metadata, indent=2) + "\n")
    return metadata
