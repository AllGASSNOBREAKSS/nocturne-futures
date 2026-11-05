"""Classify recorded job evidence without confusing data blocks with failures."""
import json
from collections import Counter


def assess_jobs(jobs, now):
    latest = {}
    for job in sorted(jobs, key=lambda item: (item["created"], item["id"])):
        payload = json.loads(job["payload"]) if isinstance(job["payload"], str) else job["payload"]
        result = (json.loads(job["result"]) if isinstance(job.get("result"), str) else job.get("result")) or {}
        lineage = result.get("symbol") or result.get("instrument") or result.get("dataset_sha256")
        key = (job["lane"], job["kind"], json.dumps(payload, sort_keys=True), lineage)
        latest[key] = job
    components = []
    for job in latest.values():
        state = job["state"]
        result = (json.loads(job["result"]) if isinstance(job.get("result"), str) else job.get("result")) or {}
        category = {"SUCCEEDED": "HEALTHY", "BLOCKED": "BLOCKED", "DEPENDENCY_BLOCKED": "BLOCKED",
                    "DISABLED": "DISABLED", "FAILED": "FAILED", "DEPENDENCY_FAILED": "FAILED"}.get(state, "DEGRADED")
        if state == "RUNNING" and 0 <= now.timestamp() - job["updated"] <= job["timeout"] + 10:
            category = "HEALTHY"
        components.append({"job_id": job["id"], "kind": job["kind"], "lane": job["lane"], "state": state,
                           "status": category, "reason": result.get("reason", state), "last_observed_at_epoch": job["updated"]})
    return {"components": components, "counts": dict(Counter(item["status"] for item in components)),
            "historical_state_counts": dict(Counter(job["state"] for job in jobs)),
            "limits": "latest recorded result per lane/type/specification, not live host liveness or a market-data entitlement"}
