"""Timestamped Phase 3P inventory; no network, training or forecast mutation."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from nocturne.research.orchestrator import JobStore

ROOT = Path(__file__).resolve().parents[1]
BASE = "ce76bf6b9144c67da11f1d0862072d023c9582ac"


def main():
    preservation = []
    for name in ("data/shadow/ndx_range/forecasts.jsonl", "data/shadow/ndx_range/outcomes.jsonl",
                 "models/shadow/ndx-range-v1/model.joblib"):
        previous = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        original_preserved = current.startswith(previous) if name.endswith(".jsonl") else current == previous
        preservation.append({"path": name, "unchanged": current == previous,
                             "original_bytes_preserved": original_preserved,
                             "appended_bytes": len(current) - len(previous) if original_preserved else None,
                             "sha256": hashlib.sha256(current).hexdigest()})
    def read(name):
        return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8-sig"))
    jobs = JobStore(ROOT / "data/research/orchestrator").jobs()
    forward = read("phase3i_forward.json")
    scheduler = read("phase3p_scheduler.json")
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "baseline_commit": BASE,
              "preservation": preservation,
              "forward": {k: forward[k] for k in ("generated_at", "issued", "verified_matured", "pending", "inference_samples")},
              "core_operations": read("phase3j_operations.json"),
              "scheduler_observation": scheduler,
              "scheduler_status": "DEGRADED" if any(t["Result"] != 0 for t in scheduler) else "LAST_EXITS_OK_NOT_UPTIME",
              "job_counts": dict(Counter(j["state"] for j in jobs)),
              "prior_ml_diagnostics": [json.loads(j["result"]) for j in jobs if j["kind"] == "MODEL_EVALUATION" and j["state"] == "SUCCEEDED"],
              "recovery": read("phase3p_recovery_check.json"),
              "futures_access": read("phase3n_futures_access.json"),
              "new_models_trained_in_phase3p": 0, "new_independent_evaluations": 0,
              "readiness": "PRE_FRONTEND_GATE_NOT_PASSED", "promotion": "NO_PROMOTION", "trading_decision": "NO_TRADE"}
    (ROOT / "reports/phase3p_evidence.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"preservation": preservation, "forward": report["forward"],
                      "scheduler_status": report["scheduler_status"], "job_counts": report["job_counts"]}))
    return 0 if all(item["original_bytes_preserved"] for item in preservation) else 1


if __name__ == "__main__":
    raise SystemExit(main())
