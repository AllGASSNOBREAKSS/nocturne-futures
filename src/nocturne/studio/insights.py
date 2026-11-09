"""Read models for intelligence, operations, research history and saved configs.

Only stored evidence is returned; missing artifacts are reported as missing.
No credential value is ever read into a response (only presence booleans).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone

import pandas as pd

from ..adapters.registry import registry
from ..research.orchestrator import JobStore
from . import ROOT, STATE, market

REPORTS = ROOT / "reports"
CONFIGS = STATE / "configs"


def _report(name):
    path = REPORTS / name
    return json.loads(path.read_text(encoding="utf-8-sig")) if path.exists() else None


def intelligence():
    a = market.archive()
    macro = {}
    for name, label in (("VIXCLS", "VIX"), ("VXNCLS", "VXN"), ("T10Y2Y", "10y-2y spread"), ("DGS10", "10y yield"),
                        ("DGS2", "2y yield"), ("BAA10Y", "Baa-10y spread"), ("WALCL", "Fed total assets"),
                        ("DTWEXBGS", "Broad dollar"), ("CPIAUCSL", "CPI index"), ("UNRATE", "Unemployment")):
        frame = a.load("fred", name)
        if frame is None or frame.empty:
            continue
        tail = frame.tail(30)
        macro[name] = {"label": label, "value": float(tail.value.iloc[-1]), "date": tail.date.iloc[-1],
                       "available_at": tail.available_at.iloc[-1], "change_20": float(tail.value.iloc[-1] - tail.value.iloc[-21]) if len(tail) > 20 else None,
                       "history": [{"date": d, "value": float(v)} for d, v in zip(frame.tail(260).date, frame.tail(260).value)],
                       "pit_eligible": bool(frame.pit_eligible.iloc[-1]), "source": "FRED"}
    cot = a.load("cftc", "tff_futures_only")
    positioning = {}
    for code, label in (("209742", "E-mini Nasdaq-100"), ("13874A", "E-mini S&P 500")):
        m = cot[cot.cftc_contract_market_code.astype(str) == code].sort_values("report_date").tail(52)
        positioning[label] = [{"report_date": r.report_date, "available_at": r.available_at, "open_interest": int(r.open_interest_all),
                               "asset_manager_net_pct": round(float((r.asset_mgr_positions_long - r.asset_mgr_positions_short) / r.open_interest_all), 4),
                               "leveraged_net_pct": round(float((r.lev_money_positions_long - r.lev_money_positions_short) / r.open_interest_all), 4)}
                              for r in m.itertuples()]
    fed = a.load("fed", "press_releases")
    sec = a.load("sec", "megacap_filings")
    bls = a.load("bls", "core_series")
    return {"macro": macro, "positioning": positioning,
            "fed_press": fed.sort_values("published_at", ascending=False).to_dict("records") if fed is not None else [],
            "sec_filings": sec.sort_values("available_at", ascending=False).head(40).to_dict("records") if sec is not None else [],
            "bls_latest": bls.sort_values("date").groupby("series").tail(1).to_dict("records") if bls is not None else [],
            "news": {"status": "BLOCKED_RATE_LIMITED", "detail": "GDELT returned HTTP 429 from this host (Phase 3U)."},
            "attribution": "FRED (St. Louis Fed), CFTC, Federal Reserve Board, SEC EDGAR, BLS; publication/availability timestamps shown."}


def _schtask(name):
    try:
        out = subprocess.run(["schtasks", "/query", "/tn", name, "/v", "/fo", "list"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return {"name": name, "status": "UNAVAILABLE"}
    fields = {}
    for line in out.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            if key.strip() in ("Status", "Last Run Time", "Last Result", "Next Run Time"):
                fields.setdefault(key.strip(), value.strip())
    return {"name": name, **fields} if fields else {"name": name, "status": "NOT_INSTALLED"}


def operations():
    def states(root):
        if not (root / "jobs.sqlite").exists():  # never create a store just to read it
            return {}
        counts = {}
        for job in JobStore(root).jobs():
            counts[job["state"]] = counts.get(job["state"], 0) + 1
        return counts
    preflight = _report("phase3v_preflight.json") or {}
    try:
        head = subprocess.run(["git", "log", "-1", "--format=%h %cI %s"], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
        branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except OSError:
        head = branch = None
    ci = None
    for name in sorted(REPORTS.glob("phase3*_ci.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:1]:
        ci = json.loads(name.read_text(encoding="utf-8-sig"))
    return {"generated_at": datetime.now(timezone.utc).isoformat(), "git": {"head": head, "branch": branch},
            "providers": registry()["providers"], "datasets": market.datasets(),
            "databento": _databento(preflight),
            "scheduler": [_schtask("Nocturne-NDX-ReadOnly-Shadow"), _schtask("Nocturne-ReadOnly-Research")],
            "orchestrator_jobs": states(ROOT / "data/research/orchestrator"), "studio_jobs": states(STATE / "jobs"),
            "shadow_operations": _report("phase3j_operations.json"), "ci": ci,
            "tests": _report("phase3u_tests.json"), "trading_decision": "NO_TRADE"}


def _databento(preflight):
    ledger_path = ROOT / "data/licensed/databento/spend_ledger.jsonl"
    ledger = [json.loads(x) for x in ledger_path.read_text().splitlines() if x.strip()] if ledger_path.exists() else []
    reserved = sum(float(e["quoted_cost_usd"]) for e in ledger if e["event"] == "RESERVED")
    completed = [e for e in ledger if e["event"] == "COMPLETED"]
    acquisition = _report("phase4_databento_acquisition.json") or {}
    quality = _report("phase4_databento_quality.json") or {}
    uncertain = {e["chunk_id"] for e in ledger if e["event"] == "RESERVED"} - {e["chunk_id"] for e in completed}
    return {"credential_present": bool(os.environ.get("DATABENTO_API_KEY")) or (ROOT / "data/security/databento.key").exists(),
            "status": ("ACQUIRED" if acquisition.get("status") == "COMPLETED" else acquisition.get("status") or "NOT_ACQUIRED")
                      + (f"; {len(uncertain)} uncertain reservation(s) need review" if uncertain else ""),
            "spend_usd": round(reserved, 4), "spend_basis": "sum of provider quotes for reserved chunks; confirm in the Databento portal",
            "credit_ceiling_usd": 125, "remaining_usd": round(125 - reserved, 4),
            "chunks": [{"chunk_id": e["chunk_id"], "quoted_cost_usd": e["quoted_cost_usd"], "compressed_bytes": e.get("compressed_bytes"), "at": e["at"]} for e in completed],
            "pilot_gate": acquisition.get("pilot_gate"), "pilot_validation": acquisition.get("pilot_validation"),
            "quality": quality.get("roots"), "quotes": preflight.get("quotes"), "range": preflight.get("range"),
            "preflight_at": preflight.get("generated_at"), "live_data": False}


def research():
    v = _report("phase3v_research.json") or {}
    summary = {}
    for root, entry in v.get("roots", {}).items():
        summary[root] = {"sessions": entry.get("sessions_after_roll_exclusion"),
                         "tasks": {task: {name: {"verdict": r.get("verdict"),
                                                 "dev_delta": (r.get("development", {}).get("brier_model_minus_baseline") or {}).get("mean"),
                                                 "dev_ci": (r.get("development", {}).get("brier_model_minus_baseline") or {}).get("ci95"),
                                                 "holdout_delta": (r.get("holdout", {}).get("brier_model_minus_baseline") or {}).get("mean"),
                                                 "dev_auc": (r.get("development", {}).get("model") or {}).get("auc"),
                                                 "holdout_auc": (r.get("holdout", {}).get("model") or {}).get("auc"),
                                                 "dev_brier": (r.get("development", {}).get("model") or {}).get("brier"),
                                                 "dev_baseline_brier": (r.get("development", {}).get("trailing_baseline") or {}).get("brier"),
                                                 "increment": (r.get("increment_vs_price_logit") or {}).get("verdict")}
                                          for name, r in configs.items()} for task, configs in entry.get("tasks", {}).items()},
                         "large_moves": entry.get("large_move_frequencies"),
                         "target_before_stop": (entry.get("target_before_stop") or {}).get("summary")}
    return {"phase3v": summary, "phase3v_generated_at": v.get("generated_at"),
            "phase3u_backtest": (_report("phase3u_backtest.json") or {}).get("results", {}).get("verdicts"),
            "strategies": _report("phase3v_strategies.json"), "signal_ranking": _report("phase3v_signal_ranking.json"),
            "ndx_shadow": _report("phase3u_forward.json"),
            "phase4_backtests": _report("phase4_backtests.json"), "phase4_target_study": _report("phase4_target_study.json")}


def _slug(name):
    slug = re.sub(r"[^a-z0-9]+", "-", str(name).lower()).strip("-")[:48]
    if not slug:
        raise ValueError("a name is required")
    return slug


def save_config(kind, name, config):
    if kind not in ("strategy", "model"):
        raise ValueError("kind must be strategy or model")
    folder = CONFIGS / kind / _slug(name)
    folder.mkdir(parents=True, exist_ok=True)
    version = len(list(folder.glob("v*.json"))) + 1
    record = {"name": name, "kind": kind, "version": version, "saved_at": datetime.now(timezone.utc).isoformat(), "config": config}
    (folder / f"v{version}.json").write_text(json.dumps(record, indent=2))
    return record


def list_configs(kind):
    out = []
    for folder in sorted((CONFIGS / kind).glob("*")) if (CONFIGS / kind).exists() else []:
        versions = sorted(folder.glob("v*.json"), key=lambda p: int(p.stem[1:]))
        if versions:
            latest = json.loads(versions[-1].read_text())
            out.append({**latest, "versions": len(versions)})
    return out
