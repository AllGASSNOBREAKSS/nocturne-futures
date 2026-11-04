"""Official BLS public API adapter (CPI, PPI, employment, unemployment).

Works without a key at reduced limits; BLS_API_KEY raises them. Values are
revisions-prone and are stored with the retrieval timestamp, not treated as
point-in-time features.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import requests

UTC = timezone.utc
ENDPOINT = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
SERIES = {
    "CUUR0000SA0": "CPI-U all items, US city average, not seasonally adjusted",
    "WPUFD4": "PPI final demand",
    "CES0000000001": "Total nonfarm payrolls, seasonally adjusted",
    "LNS14000000": "Unemployment rate, seasonally adjusted",
}


def fetch_series(series: list[str], start_year: int, end_year: int,
                 key: str | None = None, transport=None) -> dict:
    if not series or any(item not in SERIES for item in series):
        raise ValueError("only approved BLS series are allowed")
    if not 1900 <= start_year <= end_year:
        raise ValueError("invalid year range")
    payload = {"seriesid": series, "startyear": str(start_year), "endyear": str(end_year)}
    key = key or os.environ.get("BLS_API_KEY")
    if key:
        payload["registrationkey"] = key
    transport = transport or requests.Session()
    response = transport.post(ENDPOINT, json=payload, timeout=(10, 60))
    if response.status_code != 200:
        raise RuntimeError(f"BLS HTTP {response.status_code}")
    data = response.json()
    if data.get("status") != "REQUEST_SUCCEEDED":
        raise RuntimeError(f"BLS status {data.get('status')}: {data.get('message')}")
    rows = []
    for block in data.get("Results", {}).get("series", []):
        series_id = block["seriesID"]
        for item in block.get("data", []):
            period = item.get("period", "")
            if not period.startswith("M") or period == "M13":
                continue  # annual average, not a monthly observation
            raw = str(item.get("value", "")).replace(",", "").strip()
            try:
                value = float(raw)
            except ValueError:
                value = None  # BLS uses "-" for unavailable observations
            rows.append({
                "series": series_id,
                "description": SERIES[series_id],
                "year": int(item["year"]),
                "period": period,
                "date": f"{item['year']}-{period[1:]}-01",
                "value": value,
                "footnotes": [note.get("text") for note in item.get("footnotes", [])],
                "retrieved_at": datetime.now(UTC).isoformat(),
                "availability_precision": "monthly_period_not_release_timestamp",
                "point_in_time_eligible": False,
            })
    return {"series": series, "start_year": start_year, "end_year": end_year,
            "rows": rows, "latest": data.get("message", [])}


def save(result: dict, root: Path) -> dict:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = root / f"bls_{stamp}.json"
    path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return {"path": str(path), "rows": len(result["rows"]), "series": result["series"]}
