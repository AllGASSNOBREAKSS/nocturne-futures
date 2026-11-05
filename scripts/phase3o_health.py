"""Read-only component assessment; no predictions, alerts or provider requests."""
from datetime import datetime, timezone
import json
from pathlib import Path

from nocturne.adapters.snapshots import canonical, digest, immutable_write
from nocturne.research.orchestrator import JobStore
from nocturne.research.health import assess_jobs

ROOT = Path(__file__).resolve().parents[1]


def main():
    now = datetime.now(timezone.utc)
    def snapshot(name):
        try:
            return json.loads((ROOT / "reports" / name).read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            return {"status": "REPORT_UNAVAILABLE"}
    operations = snapshot("phase3j_operations.json")
    state = ROOT / "data/research/orchestrator"
    jobs = JobStore(state).jobs() if (state / "jobs.sqlite").exists() else []
    research = assess_jobs(jobs, now)
    report = {"generated_at": now.isoformat(), "shadow": operations,
              "research": research, "forward": snapshot("phase3l_forward_audit.json"),
              "core_status": "HEALTHY" if operations.get("status") == "ok" else "DEGRADED",
              "dependencies": {"authentic_futures": {"status": "BLOCKED" if not research["components"] or any(c["status"] == "BLOCKED" and c["kind"] == "HISTORICAL_BACKTEST" for c in research["components"]) else "REQUIRES_RECEIPT_REVIEW",
                                                        "reason": "see content-addressed raw-contract jobs; no paid access or model promotion performed"},
                               "challenger_auto_training": {"status": "DISABLED", "reason": "no new information-qualified research protocol enabled by default"}},
              "promotion": "NO_PROMOTION", "trading_decision": "NO_TRADE",
              "limits": "timestamped same-host evidence; not a 24/7 availability or exchange-finality claim"}
    report["overall_status"] = ("DEGRADED" if report["core_status"] != "HEALTHY" or research["counts"].get("FAILED", 0)
                                else "DEPENDENCIES_BLOCKED" if research["counts"].get("BLOCKED", 0) else "HEALTHY")
    immutable_write(state / "health_reports" / f"{digest(canonical(report))}.json", canonical(report))
    (ROOT / "reports/phase3o_operations.json").write_text(json.dumps(report, indent=2) + "\n")
    lines = ["# Component health", "", f"As of {now.isoformat()}", "", f"Core: {report['core_status']}", ""]
    for name, item in operations.get("components", {}).items():
        lines.append(f"- {name}: **{item['status']}** — {item['reason']}")
    for component in research["components"]:
        lines.append(f"- {component['kind']} / {component['job_id']}: **{component['status']}** — {component['reason']}")
    lines += ["", "Futures availability is separate from core software health. NO_PROMOTION / NO_TRADE.",
              "No new challenger protocol enabled by default. Awake, logged-in host required."]
    (ROOT / "reports/phase3o_operations.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"core_status": report["core_status"], "research_counts": research["counts"]}))
    return 0 if report["core_status"] == "HEALTHY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
