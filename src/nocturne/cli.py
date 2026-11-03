"""Command line entry point.

Existing: build | score | dashboard
v2 backend: audit | train | forecast | serve
"""

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
REGISTRY = ROOT / "models" / "registry"
JOURNAL = ROOT / "data" / "journal"
CSV_DIR = ROOT / "data" / "studies" / "daily_15y"


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


def _audit() -> int:
    from .instruments import list_instruments
    from .journal import PredictionJournal
    from .ml.registry import latest_model_id

    print("INSTRUMENTS")
    for spec in list_instruments():
        print(
            f"  {spec.instrument_id:4s} {spec.venue:5s} tick={spec.tick_size:<10.6f} "
            f"mult={spec.multiplier:<7.1f} months={spec.contract_months}"
        )
    print("\nDATA")
    for path in sorted(CSV_DIR.glob("*.csv")):
        rows = sum(1 for _ in path.open("r", encoding="utf-8")) - 1
        print(f"  {path.name:8s} {rows:5d} rows")
    print("\nMODELS")
    models = sorted(REGISTRY.glob("*/metadata.json")) if REGISTRY.exists() else []
    print(f"  registry entries: {len(models)}")
    print(f"  latest: {latest_model_id(REGISTRY)}")
    print("\nJOURNAL")
    journal = PredictionJournal(JOURNAL)
    print(f"  predictions: {len(journal.all_predictions())}")
    print(f"  outcomes:    {len(journal.outcomes())}")
    print("\nAPI: read-only; no order endpoints")
    return 0


def _train(instrument: str) -> int:
    from .pipeline import train_instrument

    summary = train_instrument(instrument)
    print(f"instrument      {summary['instrument']}")
    print(f"best model      {summary['best_model']}")
    print(f"promotion       {summary['promotion_status']}")
    print(f"samples         {summary['samples']}")
    print(f"model_id        {summary['model_id']}")
    print()
    print(f"{'model':<24}{'n':>7}{'brier':>9}{'logloss':>10}{'acc':>8}{'ece':>8}")
    for name, metrics in summary["models"].items():
        if "error" in metrics:
            print(f"{name:<24}  ERROR {metrics['error']}")
            continue
        print(
            f"{name:<24}{metrics['n']:>7}{metrics['brier']:>9.4f}"
            f"{metrics['log_loss']:>10.4f}{metrics['accuracy']:>8.3f}{metrics['ece']:>8.4f}"
        )
    return 0


def _forecast(instrument: str) -> int:
    from .pipeline import make_forecast

    prediction = make_forecast(instrument)
    print(f"prediction_id   {prediction.prediction_id}")
    print(f"instrument      {prediction.instrument_id}")
    print(f"asof            {prediction.asof_utc.isoformat()}")
    print(f"bias            {prediction.bias.value}")
    print(f"decision        {prediction.decision.value}")
    print(f"regime          {prediction.market_regime}")
    print(f"entry ticks     {prediction.entry.lower_price_ticks}-{prediction.entry.upper_price_ticks}")
    print(f"stop ticks      {prediction.stop.lower_price_ticks}-{prediction.stop.upper_price_ticks}")
    print(f"targets         {[t.zone.lower_price_ticks for t in prediction.targets]}")
    print(f"model           {prediction.model_version}")
    print(f"reasons         {prediction.reason_codes}")
    return 0


def _serve(host: str, port: int) -> int:
    import uvicorn

    uvicorn.run("nocturne.api.app:app", host=host, port=port, log_level="info")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="nocturne", description="Nocturne futures platform")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="render a dated call and, if available, its scorecard")
    build.add_argument("--date", required=True, help="call id, e.g. 2026-10-27")

    score = sub.add_parser("score", help="score the call that covers a session")
    score.add_argument("--date", required=True, help="session, e.g. 2026-10-28")

    dash = sub.add_parser("dashboard", help="build the combined HTML dashboard")
    dash.add_argument("--date", required=True, help="call id, e.g. 2026-10-27")

    sub.add_parser("audit", help="print instruments, data, models and journal status")

    train = sub.add_parser("train", help="walk-forward train the daily barrier baselines")
    train.add_argument("--instrument", default="NQ")

    forecast = sub.add_parser("forecast", help="emit a RESEARCH_ONLY forecast and journal it")
    forecast.add_argument("--instrument", default="NQ")

    serve = sub.add_parser("serve", help="run the read-only FastAPI service")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)

    context = sub.add_parser("context", help="build intermarket and premarket artifacts")
    context.add_argument("--offline", action="store_true", help="skip Yahoo intraday fetch")

    args = parser.parse_args(argv)

    if args.command == "audit":
        return _audit()
    if args.command == "train":
        return _train(args.instrument)
    if args.command == "forecast":
        return _forecast(args.instrument)
    if args.command == "serve":
        return _serve(args.host, args.port)
    if args.command == "context":
        from .context_builder import build_context

        result = build_context(offline=args.offline)
        print(json.dumps(result, indent=2)[:2000])
        return 0

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
