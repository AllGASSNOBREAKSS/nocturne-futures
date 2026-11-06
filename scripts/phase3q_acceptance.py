"""Evidence inventory, not a score, model-promotion engine or deployment approval."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess

from nocturne.research.orchestrator import JobStore

ROOT = Path(__file__).resolve().parents[1]
BASE = "84a4ea9ec5830392c2536d675886eff764f74c96"


def read(name):
    return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8-sig"))


def main():
    preservation = []
    for name in ("data/shadow/ndx_range/forecasts.jsonl", "data/shadow/ndx_range/outcomes.jsonl",
                 "models/shadow/ndx-range-v1/model.joblib"):
        original = subprocess.check_output(["git", "show", f"{BASE}:{name}"], cwd=ROOT)
        current = (ROOT / name).read_bytes()
        intact = current.startswith(original) if name.endswith(".jsonl") else current == original
        preservation.append({"path": name, "original_bytes_preserved": intact,
                             "appended_bytes": len(current) - len(original) if intact else None,
                             "sha256": hashlib.sha256(current).hexdigest()})
    forward = read("phase3i_forward.json")
    scheduler = read("phase3q_scheduler.json")
    environment = read("phase3q_environment.json")
    recovery = read("phase3q_recovery_check.json")
    clean_validation = read("phase3q_clean_validation.json")
    access = read("phase3q_data_access.json")
    operations = read("phase3j_operations.json")
    gates = [
        {"id": "orchestration", "dimension": "engineering", "status": "VERIFIED_BOUNDED" if clean_validation["job"]["state"] == "SUCCEEDED" else "BLOCKED",
         "evidence": ["reports/phase3q_clean_validation.json", "tests/test_research_orchestrator.py"],
         "missing": "hard process-memory isolation and long-duration restart/load testing"},
        {"id": "scheduled_completion", "dimension": "engineering", "status": scheduler["Status"],
         "evidence": ["reports/phase3q_scheduler.json", "reports/phase3q_hidden_experiment.json", "reports/phase3q_host_diagnostics.json"],
         "missing": "control-event sender unconfirmed; logoff/reboot and unattended service-account acceptance not tested"},
        {"id": "forward_evaluation", "dimension": "engineering", "status": forward["outcome_verification"]["status"],
         "evidence": ["reports/phase3l_forward_audit.json", "reports/phase3i_forward.json"],
         "missing": "independent exchange finality and statistically adequate forward samples"},
        {"id": "frozen_registry", "dimension": "engineering", "status": "VERIFIED_IMMUTABLE_BASE" if all(p["original_bytes_preserved"] for p in preservation) else "AUDIT_BLOCKED",
         "evidence": preservation, "missing": "independent model-promotion evidence; no automatic promotion permitted"},
        {"id": "native_and_dependencies", "dimension": "engineering", "status": environment["status"],
         "evidence": ["reports/phase3q_environment.json", "requirements/windows-py314.lock.txt", "reports/phase3q_dependency_incident.json"],
         "missing": "separate OS installation and cross-platform dependency/artifact portability"},
        {"id": "clean_host_off_host_recovery", "dimension": "engineering", "status": "PARTIAL_SAME_HOST_ONLY",
         "evidence": ["reports/phase3q_recovery_check.json", "docs/PHASE3Q_DEPLOYMENT.md"],
         "missing": "authorized private off-host destination, separate-machine restore and operational cutover/rollback drill"},
        {"id": "api_security_monitoring", "dimension": "engineering", "status": "PARTIAL_READ_ONLY_REGRESSION_SCOPE",
         "evidence": ["tests/test_api.py", "tests/test_shadow_operations.py", "docs/PHASE3Q_DEPLOYMENT.md"],
         "missing": "deployment authentication/security/load review and independent monitoring/paging"},
        {"id": "historical_backtest_ml", "dimension": "engineering", "status": "VERIFIED_DEVELOPMENT_SCOPE_ONLY",
         "evidence": ["reports/phase3q_recovery_check.json", "tests/test_daily_experiment.py", "tests/test_backtest_regression.py"],
         "missing": "authentic independent futures validation; old exposed index diagnostics are not new experiments"},
        {"id": "authentic_futures", "dimension": "quantitative", "status": access["Status"],
         "evidence": ["reports/phase3q_data_access.json", "docs/PHASE3P_DATA_ACCESS.md"],
         "missing": "configured key, license/entitlement checks, actual quotes and explicit consumption approval"},
        {"id": "independent_direction_strategy_targets", "dimension": "quantitative", "status": "BLOCKED_INSUFFICIENT_AUTHENTIC_DATA",
         "evidence": ["docs/PHASE3Q_FINDINGS.md", "docs/PHASE3N_DATA_DECISION.md"],
         "missing": "independent observations, cost-valid strategy paths and calibrated target-first/event probabilities"},
        {"id": "forward_sample_adequacy", "dimension": "quantitative", "status": "INSUFFICIENT",
         "evidence": forward["inference_samples"], "missing": "adequate genuine outcomes per frozen inference cohort"},
    ]
    jobs = JobStore(ROOT / "data/research/orchestrator").jobs()
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "baseline_commit": BASE,
              "decision": "NO_GO_FRONTEND", "gates": gates, "preservation": preservation,
              "forward": {key: forward[key] for key in ("generated_at", "issued", "verified_matured", "pending", "inference_samples", "outcome_verification")},
              "core_operations": operations, "job_counts": dict(Counter(j["state"] for j in jobs)),
              "recovery": recovery, "futures_access": access,
              "new_market_models_trained": 0, "new_independent_holdout_evaluations": 0,
              "promotion": "NO_PROMOTION", "trading_decision": "NO_TRADE",
              "limitations": "Timestamped evidence inventory. Gate review remains NO-GO despite bounded engineering success; no completion percentage or predictive-accuracy claim."}
    (ROOT / "reports/phase3q_acceptance.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"decision": report["decision"], "issued": forward["issued"], "verified_matured": forward["verified_matured"],
                      "pending": forward["pending"], "scheduler": scheduler["Status"], "job_counts": report["job_counts"]}))
    return 0 if all(p["original_bytes_preserved"] for p in preservation) else 1


if __name__ == "__main__":
    raise SystemExit(main())
