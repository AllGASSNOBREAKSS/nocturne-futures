"""Command line entry point: `nocturne build|score|dashboard`."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import Call
from .report import build_reports

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOTS = ROOT / "data" / "snapshots"
REPORTS = ROOT / "reports"
STUDY = ROOT / "data" / "studies" / "fomc_2024_2026.json"
HISTORY = ROOT / "data" / "raw" / "history_1mo.json"


def _load(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"missing file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _call_for_date(call_id: str) -> Call:
    return Call.load(SNAPSHOTS / call_id / "call.json")


def _call_for_session(session: str) -> Call:
    for path in sorted(SNAPSHOTS.glob("*/call.json")):
        call = Call.load(path)
        if call.session == session:
            return call
    raise SystemExit(f"no call found for session {session}")


def _actual_for_session(session: str) -> dict | None:
    path = SNAPSHOTS / session / "actual.json"
    return _load(path) if path.exists() else None


def _build(call: Call) -> dict[str, Path]:
    study = _load(STUDY)
    history = _load(HISTORY)
    actual = _actual_for_session(call.session)
    return build_reports(call, study, history, actual, REPORTS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nocturne", description="Overnight futures outlook engine")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="render a dated call and, if available, its scorecard")
    build.add_argument("--date", required=True, help="call id, e.g. 2026-10-27")

    score = sub.add_parser("score", help="score the call that covers a session")
    score.add_argument("--date", required=True, help="session, e.g. 2026-10-28")

    dash = sub.add_parser("dashboard", help="build the combined HTML dashboard")
    dash.add_argument("--date", required=True, help="call id, e.g. 2026-10-27")

    args = parser.parse_args(argv)

    if args.command == "build":
        call = _call_for_date(args.date)
    elif args.command == "score":
        call = _call_for_session(args.date)
    else:
        call = _call_for_date(args.date)

    outputs = _build(call)
    for name, path in outputs.items():
        print(f"{name:12s} {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
