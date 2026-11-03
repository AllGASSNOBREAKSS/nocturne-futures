"""Official real-time vintage observations, conservatively available next UTC day.

ALFRED realtime_start is a DATE, not an economic release clock time. This
adapter cannot supply intraday news, schedules or consensus. Original date
precision is retained, and records are not converted into invented events.
"""
import os
import pandas as pd
import requests


def fetch_vintage(series, vintage, key=None, transport=None):
    key = key or os.environ.get("FRED_API_KEY")
    if not key:
        raise ValueError("DATA_BLOCKED: FRED_API_KEY missing")
    day = pd.Timestamp(vintage).date().isoformat()
    transport = transport or requests.Session()
    records, offset = [], 0
    while True:
        response = transport.get("https://api.stlouisfed.org/fred/series/observations",
            params={"series_id": series, "api_key": key, "file_type": "json",
                    "realtime_start": day, "realtime_end": day, "limit": 100000, "offset": offset},
            timeout=(10, 60))
        if response.status_code != 200:
            raise RuntimeError(f"FRED HTTP {response.status_code}")
        data = response.json()
        observations = data["observations"]
        for row in observations:
            # Snapshot requested on vintage day, even if a value's original
            # realtime_start precedes it. Never claim earlier availability.
            records.append({"series": series, "date": row["date"],
                            "value": None if row["value"] == "." else float(row["value"]),
                            "realtime_start": row["realtime_start"], "realtime_end": row["realtime_end"],
                            "snapshot_vintage": day,
                            "available_at": (pd.Timestamp(day, tz="UTC") + pd.Timedelta("1D")).isoformat(),
                            "availability_precision": "conservative_next_day_not_release_timestamp",
                            "source": "FRED_ALFRED_API", "consensus": None})
        offset += len(observations)
        if offset >= int(data["count"]):
            break
        if not observations:
            raise ValueError("incomplete vintage pagination")
    return records


def visible_vintages(records, asof):
    frame = pd.DataFrame(records)
    if frame.empty:
        return frame
    known = frame[pd.to_datetime(frame.available_at, utc=True) <= pd.Timestamp(asof)]
    return known.sort_values("available_at").drop_duplicates(["series", "date"], keep="last")
