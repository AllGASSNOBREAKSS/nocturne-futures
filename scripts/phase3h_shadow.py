"""Run the read-only NDX range shadow forecast service.

Examples:
  python scripts/phase3h_shadow.py --status
  python scripts/phase3h_shadow.py --health
  python scripts/phase3h_shadow.py --once --refresh
  python scripts/phase3h_shadow.py --evaluate-only --refresh
  python scripts/phase3h_shadow.py --loop --interval-minutes 60 --refresh

The service never places orders. It writes forecasts before outcomes, records
missed sessions instead of backfilling them, and only evaluates a forecast once
the target session bar is available.
"""
import argparse
import json
import os
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

from nocturne.adapters.yahoo_history import fetch_daily_history, load_history
from nocturne.shadow import (ShadowStore, audit_forecasts, evaluate_matured,
                             evaluation_summary, generate, health, load_artifact,
                             record_missed)
from nocturne.shadow.locking import FileLock

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "ndx-range-v1"
RESEARCH_DIR = ROOT / "data/history/yahoo_daily"
OPERATIONAL_DIR = ROOT / "data/shadow/market"
STORE_DIR = ROOT / "data/shadow/ndx_range"
STATUS_PATH = ROOT / "reports/phase3h_shadow_status.json"
LOCK_PATH = STORE_DIR / "run.lock"
_RUN_LOCK = None


def acquire_lock() -> bool:
    global _RUN_LOCK
    if _RUN_LOCK is not None:
        return False
    lock = FileLock(LOCK_PATH)
    if not lock.acquire(blocking=False):
        return False
    _RUN_LOCK = lock
    return True


def release_lock() -> None:
    global _RUN_LOCK
    if _RUN_LOCK is not None:
        _RUN_LOCK.release()
        _RUN_LOCK = None


def refresh() -> dict:
    OPERATIONAL_DIR.mkdir(parents=True, exist_ok=True)
    result = {}
    for symbol in ("^NDX", "^VIX"):
        try:
            manifest = fetch_daily_history(symbol, OPERATIONAL_DIR)
            result[symbol] = {"status": "FETCHED", "last": manifest["last"], "rows": manifest["rows"]}
        except Exception as exc:  # adapter boundary
            result[symbol] = {"status": "FETCH_FAILED", "error_type": type(exc).__name__}
    return result


def load_bars(symbol: str, now=None):
    now = now or datetime.now(timezone.utc)
    name = symbol.replace("^", "IDX_").replace("=", "_")
    manifest = json.loads((OPERATIONAL_DIR / "manifests" / f"{name}.json").read_text())
    import pandas as pd
    age = (now - pd.Timestamp(manifest["received_at"]).to_pydatetime()).total_seconds()
    if not 0 <= age <= 36 * 3600 or manifest["symbol"] != symbol or manifest["frequency"] != "1d":
        raise ValueError("stale or wrong-identity operational snapshot")
    normalized = OPERATIONAL_DIR / "normalized" / f"{name}.csv"
    if hashlib.sha256(normalized.read_bytes()).hexdigest() != manifest["normalized_sha256"]:
        raise ValueError("operational snapshot checksum mismatch")
    raw = OPERATIONAL_DIR / "raw" / f"{name}_{manifest['raw_sha256']}.json"
    if hashlib.sha256(raw.read_bytes()).hexdigest() != manifest["raw_sha256"]:
        raise ValueError("raw snapshot checksum mismatch")
    frame = load_history(OPERATIONAL_DIR, symbol)
    if "source_complete" not in frame:
        raise ValueError("snapshot lacks OHLC completeness evidence; refresh required")
    from nocturne.adapters.snapshots import SnapshotStore
    identifier = manifest.get("snapshot_id")
    if not identifier:
        raise ValueError("immutable snapshot missing; refresh required")
    archived = SnapshotStore(OPERATIONAL_DIR / "snapshots").manifest(identifier)
    if (archived["raw_sha256"] != manifest["raw_sha256"]
            or archived["normalized_sha256"] != manifest["normalized_sha256"]
            or archived["source"]["received_at"] != manifest["received_at"]):
        raise ValueError("mutable cache does not match archived snapshot")
    frame = frame[frame.source_complete.eq(True)]
    frame.attrs["snapshot_id"] = identifier
    return frame, str(OPERATIONAL_DIR)


def write_status(status):
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary = STATUS_PATH.with_suffix(".tmp")
    temporary.write_text(json.dumps(status, indent=2, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, STATUS_PATH)


def cycle(refresh_data: bool, now: datetime | None = None, evaluate_only: bool = False) -> dict:
    wall_clock = now is None
    now = now or datetime.now(timezone.utc)
    store = ShadowStore(STORE_DIR)
    if not acquire_lock():
        store.log("LOCK_HELD", "WARNING")
        return {"status": "LOCKED", "reason": "another cycle is running"}
    try:
        store.ensure_started(now, MODEL_ID)
        missed = record_missed(store, None, now)
        refresh_result = refresh() if refresh_data else {}
        if wall_clock:
            now = datetime.now(timezone.utc)
        try:
            index, index_source = load_bars("^NDX", now)
            vix, vix_source = load_bars("^VIX", now)
        except (FileNotFoundError, ValueError, KeyError) as exc:
            store.record_quality_failure("MARKET_DATA_MISSING", {"error": str(exc)})
            store.log("CYCLE_FAILED", "ERROR", {"reason": "MARKET_DATA_MISSING"})
            blocked = {"status": "DATA_BLOCKED", "generation": "DATA_BLOCKED", "reason": "MARKET_DATA_MISSING_OR_INVALID",
                       "generated_at": now.isoformat(), "model_id": MODEL_ID,
                       "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW", "trading_decision": "NO_TRADE",
                       "operational_status": "DATA_BLOCKED",
                       "evaluation": evaluation_summary(store), "refresh": refresh_result,
                       "latest_forecast": store.latest(), "detail": str(exc)}
            write_status(blocked)
            return blocked
        artifact = load_artifact(ROOT / "models/shadow", MODEL_ID)
        sources = {"index": str(Path(index_source).relative_to(ROOT)).replace("\\", "/"),
                   "vix": str(Path(vix_source).relative_to(ROOT)).replace("\\", "/"),
                   "refresh": refresh_result}
        sources["manifests"] = {name: json.loads((OPERATIONAL_DIR / "manifests" / f"{stem}.json").read_text())
                                for name, stem in (("index", "IDX_NDX"), ("vix", "IDX_VIX"))}
        sources["snapshot_ids"] = {name: manifest["snapshot_id"] for name, manifest in sources["manifests"].items()}
        generated = ({"status": "EVALUATE_ONLY"} if evaluate_only else
                     generate(artifact, store, index, vix, now,
                               validation_status=artifact.metadata["validation_status"],
                               source=sources, issuance_clock=(lambda: datetime.now(timezone.utc)) if wall_clock else None))
        audit = audit_forecasts(store, index, snapshot_root=OPERATIONAL_DIR / "snapshots")
        failed_ids = {item["forecast_id"] for item in audit["failed"]}
        allowed_ids = {item["forecast_id"] for item in store.forecasts()} - failed_ids
        # Quarantine failed forecasts individually; one revised historical
        # reference must not suppress unrelated verified outcomes indefinitely.
        proof_ids = {item["forecast_id"]: [item["reconciliation_id"]] for item in audit["records"]
                     if item["ok"] and item.get("reconciliation_id")}
        matured = evaluate_matured(store, index, now, allowed_forecast_ids=allowed_ids,
                                   verified_reconciliation_ids=proof_ids)
        summary = evaluation_summary(store)
        latest = store.latest()
        generation_failed = generated.get("status") == "SKIPPED" and generated.get("reason") != "TOO_LATE_FOR_TARGET"
        event = "CYCLE_AUDIT_FAILED" if audit["failed"] else "CYCLE_FAILED" if generation_failed else "CYCLE_OK"
        store.log(event, now=now, detail={"generation": generated.get("status"),
                                      "matured": len(matured), "missed": len(missed),
                                      "audit_failed": len(audit["failed"])})
        state = health(store, now)
        status = {
            "generated_at": now.isoformat(),
            "model_id": artifact.model_id,
            "model_version": artifact.version,
            "validation_status": artifact.metadata["validation_status"],
            "trading_decision": "NO_TRADE",
            "mode": "read_only_shadow",
            "operational_status": "AUDIT_BLOCKED" if audit["failed"] else "CYCLE_FAILED" if generation_failed else "SHADOW_ACTIVE",
            "generation": generated.get("status"),
            "generation_detail": {k: v for k, v in generated.items() if k != "forecast"},
            "latest_forecast": latest,
            "matured_now": len(matured),
            "missed_now": len(missed),
            "audit": audit,
            "health": state,
            "evaluation": summary,
            "refresh": refresh_result,
            "sources": sources,
            "notes": ["forecasts are range quantiles for the NDX cash session, not NQ futures",
                      "no trading signal is produced",
                      "forward accuracy is not claimed before maturity"],
        }
        write_status(status)
        return status
    except Exception as exc:
        # One-shot scheduled execution needs the same durable failure signal as
        # loop mode. Do not retain stale success or log exception text/secrets.
        store.log("CYCLE_EXCEPTION", "ERROR", {"error_type": type(exc).__name__}, now=now)
        failed = {"generated_at": now.isoformat(), "model_id": MODEL_ID,
                  "generation": "CYCLE_EXCEPTION", "operational_status": "CYCLE_FAILED",
                  "reason": type(exc).__name__, "validation_status": "RESEARCH_VALIDATED_PENDING_SHADOW",
                  "trading_decision": "NO_TRADE", "mode": "read_only_shadow"}
        write_status(failed)
        return failed
    finally:
        release_lock()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--evaluate-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--interval-minutes", type=float, default=60.0)
    args = parser.parse_args()
    if args.status:
        print(STATUS_PATH.read_text(encoding="utf-8") if STATUS_PATH.exists()
              else json.dumps({"status": "NO_RUN_YET"}))
        return 0
    if args.health:
        state = health(ShadowStore(STORE_DIR), datetime.now(timezone.utc))
        print(json.dumps(state, indent=2))
        return 0 if state["status"] == "ok" else 1
    if args.loop:
        if args.interval_minutes < 1:
            raise SystemExit("interval must be at least one minute")
        while True:
            try:
                result = cycle(args.refresh, evaluate_only=args.evaluate_only)
                print(json.dumps({"at": result.get("generated_at"), "generation": result.get("generation"),
                                  "matured": result.get("evaluation", {}).get("matured")}))
            except Exception as exc:  # keep the service alive but record the failure
                ShadowStore(STORE_DIR).record_quality_failure(
                    "CYCLE_EXCEPTION", {"error_type": type(exc).__name__})
                ShadowStore(STORE_DIR).log("CYCLE_EXCEPTION", "ERROR",
                                           {"error_type": type(exc).__name__})
                print(json.dumps({"error": type(exc).__name__}))
            time.sleep(args.interval_minutes * 60)
    result = cycle(args.refresh, evaluate_only=args.evaluate_only)
    print(json.dumps({k: result.get(k) for k in ("generated_at", "generation", "model_id",
                                                 "validation_status", "trading_decision")}, indent=2))
    return 1 if result.get("operational_status") in {"DATA_BLOCKED", "AUDIT_BLOCKED", "CYCLE_FAILED"} else 0


if __name__ == "__main__":
    raise SystemExit(main())
