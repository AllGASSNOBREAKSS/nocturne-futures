"""Run the read-only NDX range shadow forecast service.

Examples:
  python scripts/phase3h_shadow.py --status
  python scripts/phase3h_shadow.py --once --refresh
  python scripts/phase3h_shadow.py --loop --interval-minutes 60 --refresh

The service never places orders. It writes forecasts before outcomes and only
evaluates a forecast once the target session bar is available.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from nocturne.adapters.yahoo_history import fetch_daily_history, load_history
from nocturne.shadow import (ShadowStore, evaluate_matured, evaluation_summary,
                             generate, load_artifact)

ROOT = Path(__file__).resolve().parents[1]
MODEL_ID = "ndx-range-v1"
RESEARCH_DIR = ROOT / "data/history/yahoo_daily"
OPERATIONAL_DIR = ROOT / "data/shadow/market"
STORE_DIR = ROOT / "data/shadow/ndx_range"
STATUS_PATH = ROOT / "reports/phase3h_shadow_status.json"


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


def load_bars(symbol: str):
    for directory in (OPERATIONAL_DIR, RESEARCH_DIR):
        try:
            frame = load_history(directory, symbol)
            if not frame.empty:
                return frame, str(directory)
        except FileNotFoundError:
            continue
    raise FileNotFoundError(f"no data for {symbol}")


def cycle(refresh_data: bool, now: datetime | None = None, evaluate_only: bool = False) -> dict:
    now = now or datetime.now(timezone.utc)
    store = ShadowStore(STORE_DIR)
    refresh_result = refresh() if refresh_data else {}
    try:
        index, index_source = load_bars("^NDX")
        vix, vix_source = load_bars("^VIX")
    except FileNotFoundError as exc:
        store.record_quality_failure("MARKET_DATA_MISSING", {"error": str(exc)})
        return {"status": "DATA_BLOCKED", "reason": "MARKET_DATA_MISSING", "detail": str(exc)}
    artifact = load_artifact(ROOT / "models/shadow", MODEL_ID)
    sources = {"index": str(Path(index_source).relative_to(ROOT)).replace("\\", "/"),
               "vix": str(Path(vix_source).relative_to(ROOT)).replace("\\", "/"),
               "refresh": refresh_result}
    generated = ({"status": "EVALUATE_ONLY"} if evaluate_only else
                 generate(artifact, store, index, vix, now,
                          validation_status=artifact.metadata["validation_status"],
                          source=sources))
    matured = evaluate_matured(store, index, now)
    summary = evaluation_summary(store)
    latest = store.latest()
    status = {
        "generated_at": now.isoformat(),
        "model_id": artifact.model_id,
        "model_version": artifact.version,
        "validation_status": artifact.metadata["validation_status"],
        "trading_decision": "NO_TRADE",
        "mode": "read_only_shadow",
        "generation": generated.get("status"),
        "generation_detail": {k: v for k, v in generated.items() if k != "forecast"},
        "latest_forecast": latest,
        "matured_now": len(matured),
        "evaluation": summary,
        "refresh": refresh_result,
        "sources": sources,
        "notes": ["forecasts are range quantiles for the NDX cash session, not NQ futures",
                  "no trading signal is produced", "forward accuracy is not claimed before maturity"],
    }
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(status, indent=2, default=str) + "\n", encoding="utf-8")
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--evaluate-only", action="store_true")
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--interval-minutes", type=float, default=60.0)
    args = parser.parse_args()
    if args.status:
        print(STATUS_PATH.read_text(encoding="utf-8") if STATUS_PATH.exists()
              else json.dumps({"status": "NO_RUN_YET"}))
        return 0
    if args.loop:
        if args.interval_minutes < 1:
            raise SystemExit("interval must be at least one minute")
        while True:
            try:
                result = cycle(args.refresh)
                print(json.dumps({"at": result.get("generated_at"), "generation": result.get("generation"),
                                  "matured": result.get("evaluation", {}).get("matured")}))
            except Exception as exc:  # keep the service alive but record the failure
                ShadowStore(STORE_DIR).record_quality_failure(
                    "CYCLE_EXCEPTION", {"error_type": type(exc).__name__})
                print(json.dumps({"error": type(exc).__name__}))
            time.sleep(args.interval_minutes * 60)
    result = cycle(args.refresh, evaluate_only=args.evaluate_only)
    print(json.dumps({k: result.get(k) for k in ("generated_at", "generation", "model_id",
                                                 "validation_status", "trading_decision")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
