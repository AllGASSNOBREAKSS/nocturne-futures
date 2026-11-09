"""Session range forecasts (Asia / London / New York / full Globex day).

Method `trailing-empirical-v1`: P50/P80/P90 of each session's high-low range
over the trailing 250 completed sessions. It is a transparent baseline, not a
validated model; direction is never forecast. Records are append-only:
issuance never changes, outcomes are separate rows written once.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from ..shadow.locking import FileLock
from . import STATE, market

METHOD = "trailing-empirical-v1"
QUANTILES = (0.5, 0.8, 0.9)
WINDOW = 250
DIR = STATE / "forecasts"


def _lines(path):
    return [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines() if x.strip()] if path.exists() else []


def _append(path, record):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")


def _ranges(root):
    sessions, meta = market.session_ranges(root)
    daily, _ = market.bars(root, "1d", limit=100000)
    from .indicators import globex_session
    day = pd.DataFrame({"session_date": globex_session(daily.timestamp + pd.Timedelta(hours=12)),
                        "range": (daily.high - daily.low).to_numpy(), "session": "FULL_DAY"})
    return pd.concat([sessions[["session_date", "range", "session"]], day], ignore_index=True), meta


def _next_business_day(day):
    day = pd.Timestamp(day) + pd.Timedelta(days=1)
    while day.weekday() >= 5:
        day += pd.Timedelta(days=1)
    return day.date()


def issue(root):
    ranges, meta = _ranges(root)
    hourly, _ = market.bars(root, "1h", limit=3)
    complete = ranges[ranges.session == "NEW_YORK"].session_date.max()
    target = _next_business_day(complete)
    out = {}
    for name in ("ASIA", "LONDON", "NEW_YORK", "FULL_DAY"):
        r = ranges[(ranges.session == name) & (ranges.session_date <= complete)].sort_values("session_date").tail(WINDOW)["range"]
        out[name] = {f"p{int(q * 100)}": round(float(np.quantile(r, q)), 2) for q in QUANTILES} | {"history_n": int(len(r))}
    body = {"instrument": root, "target_session": str(target), "method": METHOD, "quantiles_points": out,
            "data_as_of": str(hourly.timestamp.iloc[-1] + pd.Timedelta(hours=1)), "dataset": meta["dataset"],
            "dataset_sha256": meta["normalized_sha256"], "regime": market.regime(root),
            "levels": market.levels(root)["levels"], "direction": None,
            "direction_note": "Directional forecasts are withheld: no directional model passed independent validation (Phases 3U/3V).",
            "event_risk": "No verified forward economic calendar is configured; see Market Intelligence for past releases.",
            "validation_status": "BASELINE_RESEARCH_ONLY", "freshness": "HISTORICAL_DELAYED_NOT_REALTIME",
            "trading_decision": "NO_TRADE"}
    identity = hashlib.sha256(f"{root}|{target}|{METHOD}".encode()).hexdigest()[:24]
    path = DIR / "forecasts.jsonl"
    with FileLock(DIR / "journal.lock"):
        existing = {f["forecast_id"]: f for f in _lines(path)}
        if identity in existing:
            return {**existing[identity], "status": "ALREADY_ISSUED"}
        record = {"forecast_id": identity, "issued_at": datetime.now(timezone.utc).isoformat(), **body}
        record["record_sha256"] = hashlib.sha256(json.dumps(record, sort_keys=True, default=str).encode()).hexdigest()
        _append(path, record)
    return {**record, "status": "ISSUED"}


def evaluate():
    """Write one outcome row per completed (forecast, session); never edits forecasts."""
    written = 0
    with FileLock(DIR / "journal.lock"):
        forecasts = _lines(DIR / "forecasts.jsonl")
        done = {(o["forecast_id"], o["session"]) for o in _lines(DIR / "outcomes.jsonl")}
        cache = {}
        for f in forecasts:
            if f["instrument"] not in cache:
                cache[f["instrument"]] = _ranges(f["instrument"])[0]
            ranges = cache[f["instrument"]]
            for name, q in f["quantiles_points"].items():
                if (f["forecast_id"], name) in done:
                    continue
                hit = ranges[(ranges.session == name) & (ranges.session_date.astype(str) == f["target_session"])]
                if hit.empty:
                    continue
                y = float(hit["range"].iloc[0])
                pin = {k: round(float(max(a * (y - q[k]), (a - 1) * (y - q[k]))), 3) for k, a in (("p50", .5), ("p80", .8), ("p90", .9))}
                _append(DIR / "outcomes.jsonl", {"forecast_id": f["forecast_id"], "session": name, "realized_range": y,
                                                 "covered": {k: y <= q[k] for k in ("p50", "p80", "p90")}, "pinball": pin,
                                                 "evaluated_at": datetime.now(timezone.utc).isoformat(),
                                                 "source": "yahoo continuous futures (research-grade)"})
                written += 1
    return written


def history(root=None):
    forecasts = [f for f in _lines(DIR / "forecasts.jsonl") if root in (None, f["instrument"])]
    outcomes = _lines(DIR / "outcomes.jsonl")
    by = {}
    for o in outcomes:
        by.setdefault(o["forecast_id"], []).append(o)
    rows = [{**f, "outcomes": by.get(f["forecast_id"], [])} for f in forecasts]
    scored = [o for f in rows for o in f["outcomes"]]
    summary = {"issued": len(rows), "evaluated_sessions": len(scored),
               "coverage": {k: (round(float(np.mean([o["covered"][k] for o in scored])), 3) if scored else None) for k in ("p50", "p80", "p90")},
               "note": "Genuine forward record of the baseline method; too few observations for calibration claims until n is large."}
    return {"forecasts": rows, "summary": summary}


def retrospective_calibration(root, sessions=500):
    """Walk the same method over past sessions (retrospective, not forward evidence)."""
    ranges, _ = _ranges(root)
    out = {}
    for name in ("ASIA", "LONDON", "NEW_YORK", "FULL_DAY"):
        r = ranges[ranges.session == name].sort_values("session_date")["range"].reset_index(drop=True)
        rows = []
        for i in range(max(WINDOW, len(r) - sessions), len(r)):
            hist = r.iloc[i - WINDOW:i]
            rows.append({f"p{int(q * 100)}": r.iloc[i] <= np.quantile(hist, q) for q in QUANTILES})
        frame = pd.DataFrame(rows)
        out[name] = {"n": len(frame), **{k: round(float(frame[k].mean()), 3) for k in frame} } if len(frame) else {"n": 0}
    return {"method": METHOD, "scope": "RETROSPECTIVE", "coverage": out}
