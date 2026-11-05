"""Independently verify saved outcomes; never write forecasts or outcomes."""
import json
from datetime import datetime, timezone
from pathlib import Path

from nocturne.adapters.snapshots import SnapshotStore, digest
from nocturne.shadow import ShadowStore, load_artifact
from nocturne.shadow.outcome_audit import audit_outcomes

ROOT = Path(__file__).resolve().parents[1]


def main():
    store = ShadowStore(ROOT / "data/shadow/ndx_range")
    before = {name: path.read_bytes() if path.exists() else b"" for name, path in
              (("forecasts", store.forecast_path), ("outcomes", store.outcome_path))}
    artifact = load_artifact(ROOT / "models/shadow", "ndx-range-v1")
    report = audit_outcomes(store, SnapshotStore(ROOT / "data/shadow/market/snapshots"),
                            artifact.metadata["baseline_quantiles"])
    report.update(generated_at=datetime.now(timezone.utc).isoformat(), issued=len(store.forecasts()),
                  pending=len(store.forecasts()) - len(store.outcomes()),
                  baseline_sha256=artifact.metadata["artifact_digests"]["baseline.json"],
                  baseline_provenance="train-only comparator committed in 92cd098 before first outcome; not embedded in the first issued forecast")
    for name, path in (("forecasts", store.forecast_path), ("outcomes", store.outcome_path)):
        after = path.read_bytes() if path.exists() else b""
        if after != before[name]:
            raise ValueError("journal changed during independent audit")
    report["journal_hashes"] = {name: digest(content) for name, content in before.items()}
    (ROOT / "reports/phase3l_forward_audit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: report[key] for key in ("status", "issued", "journaled", "verified", "pending")}))
    return 1 if report["status"] == "AUDIT_BLOCKED" else 0


if __name__ == "__main__":
    raise SystemExit(main())
