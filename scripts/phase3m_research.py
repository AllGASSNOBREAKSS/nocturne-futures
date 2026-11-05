"""Enqueue cadence buckets, run bounded work, export durable job history."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

from nocturne.research.orchestrator import JobStore, run_lane
from nocturne.adapters.snapshots import canonical, digest

ROOT = Path(__file__).resolve().parents[1]


def schedule(store, lane, bucket, index_diagnostics=False):
    if lane == "shadow":
        previous = None
        for kind in ("DATA_REFRESH", "SHADOW_FORECAST", "FORECAST_MATURITY_CHECK", "FORWARD_EVALUATION", "MODEL_DRIFT_MONITOR"):
            previous = store.submit(kind, lane, bucket, dependencies=[previous] if previous else [], timeout=180)
    else:
        validated = store.submit("DATA_VALIDATION", lane, bucket)
        # Phase 3N: do not keep repeating old index-context experiments merely
        # because a day passed. Retain them as an explicit diagnostic option.
        for symbol in (("^NDX", "^GSPC") if index_diagnostics else ()):
            feature = store.submit("FEATURE_BUILD", lane, f"{bucket}|{symbol}", {"symbol": symbol}, [validated])
            store.submit("HISTORICAL_BACKTEST", lane, f"{bucket}|{symbol}", dependencies=[feature])
            split = store.submit("WALK_FORWARD_VALIDATION", lane, f"{bucket}|{symbol}", dependencies=[feature])
            train = store.submit("MODEL_TRAINING", lane, f"{bucket}|{symbol}", dependencies=[split], timeout=600, max_attempts=1)
            store.submit("MODEL_EVALUATION", lane, f"{bucket}|{symbol}", dependencies=[train], timeout=300, max_attempts=1)
        inventory = [{"name": p.name, "sha256": digest(p.read_bytes())}
                     for p in sorted((ROOT / "data/licensed/databento").glob("*.json"))]
        code = b"".join((ROOT / name).read_bytes() for name in ("src/nocturne/research/futures_pilot.py", "src/nocturne/backtest/engine.py", "src/nocturne/research/contract_replay.py", "src/nocturne/research/target_dataset.py"))
        version = digest(canonical({"receipts": inventory, "code": digest(code)}))
        for instrument, contract in (("NQ", "NQZ6"), ("ES", "ESZ6")):
            # This handler independently verifies its licensed receipts; public
            # index validation is not a dependency. Same data/code => same job
            # across dates. New/changed receipts or engine code create new work.
            store.submit("HISTORICAL_BACKTEST", lane, f"raw_futures_v3|{instrument}|{version}",
                         {"scope": "raw_futures", "instrument": instrument, "contract": contract}, max_attempts=1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=("shadow", "research"), required=True)
    parser.add_argument("--state", type=Path, default=ROOT / "data/research/orchestrator")
    parser.add_argument("--max-jobs", type=int, default=20)
    parser.add_argument("--budget-seconds", type=int, default=900)
    parser.add_argument("--no-enqueue", action="store_true")
    parser.add_argument("--index-diagnostics", action="store_true", help="explicitly request old development diagnostics; models still reuse their fixed experiment cache")
    args = parser.parse_args()
    store = JobStore(args.state)
    now = datetime.now(timezone.utc)
    # Shadow ticks are half-hourly; public validation is daily. Futures work is
    # content-addressed across dates; old index diagnostics require explicit opt-in.
    bucket = now.strftime("%Y-%m-%d") if args.lane == "research" else now.strftime("%Y-%m-%dT%H:") + ("00" if now.minute < 30 else "30")
    if not args.no_enqueue:
        schedule(store, args.lane, bucket, index_diagnostics=args.index_diagnostics)
    result = run_lane(store, ROOT, args.lane, args.max_jobs, args.budget_seconds)
    # Snapshot after the work, without dependencies that would suppress it when
    # data or training fail. Each distinct state has a separate immutable report.
    if result["status"] == "COMPLETED_TICK":
        audit_path = ROOT / "reports/phase3l_forward_audit.json"
        signature = digest(canonical({"report_code_sha256": digest((ROOT / "src/nocturne/research/jobs.py").read_bytes()),
                                       "forward_audit_sha256": digest(audit_path.read_bytes()) if audit_path.exists() else None,
                                       "jobs": [{k: j[k] for k in ("id", "state", "attempts", "updated")}
                                                for j in store.jobs() if j["kind"] != "RESEARCH_REPORT"]}))
        report_id = store.submit("RESEARCH_REPORT", args.lane, signature, timeout=60)
        run_lane(store, ROOT, args.lane, max_jobs=1, budget_seconds=60, only_ids={report_id})
        snapshot = next(j for j in store.jobs() if j["id"] == report_id)
        if snapshot["state"] == "SUCCEEDED":
            paths = json.loads(snapshot["result"])
            for extension, key in (("json", "report_path"), ("md", "markdown_path")):
                destination = ROOT / f"reports/phase3m_research.{extension}"
                temporary = destination.with_suffix(f".{args.lane}.tmp")
                temporary.write_bytes(Path(paths[key]).read_bytes())
                temporary.replace(destination)
    print(json.dumps(result))
    jobs = store.jobs()
    destination = ROOT / "reports/phase3m_jobs.json"
    temporary = destination.with_suffix(f".{args.lane}.tmp")
    temporary.write_text(json.dumps({"generated_at": now.isoformat(), "runner": result, "jobs": jobs}, indent=2) + "\n")
    temporary.replace(destination)
    return 1 if any(j["state"] in {"FAILED", "DEPENDENCY_FAILED"} and j["updated"] >= now.timestamp()
                    for j in jobs if j["lane"] == args.lane) else 0


if __name__ == "__main__":
    raise SystemExit(main())
