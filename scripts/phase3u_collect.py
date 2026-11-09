"""Collect free, legitimately accessible market/macro/event data (Phase 3U).

Each source runs independently; a blocked or failed provider is recorded and
does not stop the others. Writes reports/phase3u_collection.json.
"""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from nocturne.collector.http import PoliteClient
from nocturne.collector.sources import BLOCKED_SOURCES, COLLECTORS, INTERVALS
from nocturne.collector.store import Archive

ROOT = Path(__file__).resolve().parents[1]


def run(sources, root, report_path):
    archive = Archive(root)
    client = PoliteClient(intervals=INTERVALS)
    results = {}
    for name in sources:
        started = time.monotonic()
        try:
            entries = COLLECTORS[name](client, archive)
            results[name] = {"status": "COLLECTED", "seconds": round(time.monotonic() - started, 2),
                             "datasets": [{k: e.get(k) for k in ("dataset", "status", "rows", "first", "last", "appended_rows",
                                                                 "revised_rows", "removed_rows", "revised_examples", "raw_sha256",
                                                                 "normalized_sha256", "raw_bytes", "credibility", "pit_eligible",
                                                                 "availability_rule", "limitation", "url")}
                                          for e in entries]}
        except Exception as exc:  # recorded per source; never hides a failure as success
            results[name] = {"status": "FAILED", "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                             "seconds": round(time.monotonic() - started, 2)}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "archive_root": str(Path(root).relative_to(ROOT)),
              "sources": results, "blocked_or_not_used": BLOCKED_SOURCES, "http_log": client.log,
              "policy": "official documented APIs follow published API terms; crawl access requires robots.txt permission; "
                        "no paywall/CAPTCHA/auth bypass; rows with pit_eligible=false never enter backtests"}
    Path(report_path).write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sources", default=",".join(COLLECTORS))
    parser.add_argument("--root", type=Path, default=ROOT / "data/history/free")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/phase3u_collection.json")
    args = parser.parse_args()
    names = [s for s in args.sources.split(",") if s]
    unknown = set(names) - set(COLLECTORS)
    if unknown:
        parser.error(f"unknown sources {sorted(unknown)}")
    report = run(names, args.root, args.report)
    summary = {k: (v["status"], [(d["dataset"], d["status"], d["rows"]) for d in v.get("datasets", [])] or v.get("error"))
               for k, v in report["sources"].items()}
    print(json.dumps(summary, indent=1, default=str))
    return 0 if all(v["status"] == "COLLECTED" for v in report["sources"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
