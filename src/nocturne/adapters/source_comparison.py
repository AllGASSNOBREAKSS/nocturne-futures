"""Equivalent-series comparisons; disagreement does not identify the wrong feed."""
import math

import pandas as pd

from .snapshots import digest

IDENTITY = ("instrument", "kind", "session", "timezone", "price_basis", "currency", "frequency")


def compare_sources(left, right, left_source, right_source, tolerances):
    for key in IDENTITY:
        if not left_source.get(key) or left_source[key] != right_source.get(key):
            raise ValueError(f"incomparable source contract: {key}")
    if left_source["frequency"] != "1d":
        raise ValueError("daily comparison only; intraday needs exchange-time alignment")
    fields = sorted(set(left.columns) & set(right.columns) & {"open", "high", "low", "close", "volume"})
    if not fields or any(field not in tolerances or not math.isfinite(tolerances[field]) or tolerances[field] < 0 for field in fields):
        raise ValueError("explicit finite nonnegative tolerances required for every compared field")
    a, b = left.copy(), right.copy()
    for frame in (a, b):
        frame["date"] = pd.to_datetime(frame.date).dt.strftime("%Y-%m-%d")
        if frame.date.duplicated().any():
            raise ValueError("duplicate comparison dates")
    joined = a.merge(b, on="date", suffixes=("_left", "_right"))
    rows = []
    for _, row in joined.iterrows():
        for field in fields:
            x, y = float(row[f"{field}_left"]), float(row[f"{field}_right"])
            if not math.isfinite(x) or not math.isfinite(y):
                raise ValueError("non-finite comparison observation")
            if x != y:
                rows.append({"date": row.date, "field": field, "left": x, "right": y,
                             "absolute_difference": abs(x - y), "tolerance": tolerances[field],
                             "within_tolerance": abs(x - y) <= tolerances[field]})
    return {"status": "NO_OVERLAP" if joined.empty else "UNRESOLVED_CONFLICT" if any(not r["within_tolerance"] for r in rows) else "WITHIN_DECLARED_TOLERANCE",
            "overlap": len(joined), "differences": rows, "left_source": left_source, "right_source": right_source,
            "left_sha256": digest(left.to_csv(index=False, lineterminator="\n").encode()), "right_sha256": digest(right.to_csv(index=False, lineterminator="\n").encode()),
            "note": "comparison only; neither feed deemed authoritative; independent upstream provenance must be established separately"}


def estimate_futures_bar_volume(sessions=252, instruments=2, hours_per_session=23, csv_bytes_per_row=(150, 250)):
    if sessions < 1 or instruments < 1 or not 0 < hours_per_session <= 24:
        raise ValueError("invalid planning assumptions")
    minutes = int(sessions * instruments * hours_per_session * 60)
    return {"definition": "planning estimate, not downloaded observations, exchange schedule or billable quote",
            "assumptions": {"sessions": sessions, "instruments": instruments, "hours_per_session": hours_per_session,
                            "active_contracts_per_instrument": 1, "csv_bytes_per_row": list(csv_bytes_per_row)},
            "one_minute_rows": minutes, "five_minute_rows": minutes // 5,
            "one_minute_csv_bytes": [minutes * size for size in csv_bytes_per_row],
            "five_minute_csv_bytes": [minutes // 5 * size for size in csv_bytes_per_row],
            "limits": "roll overlap, holidays, compression and provider encoding change volume; ticks/quotes/depth require actual provider sizing"}
