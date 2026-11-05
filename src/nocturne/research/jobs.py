"""Real bounded job handlers, adapting existing shadow and research components."""
import json
import subprocess
import sys
from pathlib import Path

import pandas as pd

from ..adapters.snapshots import canonical, digest
from .daily_experiment import (PROTOCOL, verified_history, build_dataset, folds,
                               context_backtest, train_development, evaluate_development)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, default=str, allow_nan=False) + "\n")


def ancestor(store, job, kind):
    jobs = {j["id"]: j for j in store.jobs()}
    pending = json.loads(job["dependencies"])
    while pending:
        candidate = jobs[pending.pop(0)]
        if candidate["kind"] == kind:
            return json.loads(candidate["result"])
        pending.extend(json.loads(candidate["dependencies"]))
    raise ValueError(f"missing {kind} dependency")


def dataset_from(store, job):
    source = ancestor(store, job, "FEATURE_BUILD")
    path = Path(source["dataset_path"])
    if digest(path.read_bytes()) != source["dataset_sha256"]:
        raise ValueError("versioned feature dataset changed")
    data = pd.read_csv(path)
    for column in ("feature_available_at", "label_end", "entry_time"):
        data[column] = pd.to_datetime(data[column], utc=True)
    return data, source


def execute_job(kind, payload, repository, directory, store, job):
    shadow_kinds = {"DATA_REFRESH", "SHADOW_FORECAST", "FORECAST_MATURITY_CHECK", "FORWARD_EVALUATION", "MODEL_DRIFT_MONITOR"}
    if kind in shadow_kinds:
        if job["lane"] != "shadow":
            raise ValueError("shadow operations cannot run in research lane")
        commands = {
            "DATA_REFRESH": ["scripts/phase3h_shadow.py", "--evaluate-only", "--refresh"],
            "SHADOW_FORECAST": ["scripts/phase3h_shadow.py", "--once"],
            "FORECAST_MATURITY_CHECK": ["scripts/phase3h_shadow.py", "--evaluate-only"],
            "FORWARD_EVALUATION": ["scripts/phase3l_forward_audit.py"],
            "MODEL_DRIFT_MONITOR": ["scripts/phase3i_forward_report.py"],
        }
        completed = subprocess.run([sys.executable, *commands[kind]], cwd=repository)
        if completed.returncode:
            return {"status": "FAILED", "reason": "SHADOW_COMPONENT_EXIT", "exit_code": completed.returncode}
        return {"status": "SUCCEEDED", "component": commands[kind][0],
                "note": "component success does not mean an observation matured or a new forecast issued"}
    if kind == "DATA_VALIDATION":
        coverage = []
        for path in sorted((repository / "data/history/yahoo_daily/manifests").glob("*.json")):
            meta = json.loads(path.read_text())
            if meta.get("rows", 0) > 50000:
                raise ValueError("configured historical row budget exceeded")
            frame, receipt = verified_history(repository / "data/history/yahoo_daily", meta["symbol"])
            if len(frame) > 50000:
                raise ValueError("historical row budget exceeded")
            coverage.append({k: receipt.get(k) for k in ("symbol", "kind", "rows", "first", "last", "span_years", "raw_sha256", "normalized_sha256")})
        if not coverage:
            return {"status": "BLOCKED", "reason": "NO_VERIFIED_HISTORY"}
        write_json(directory / "coverage.json", coverage)
        return {"status": "SUCCEEDED", "coverage": coverage,
                "availability": "historical bar-end lower bound; not release-vintage-certified PIT"}
    if kind == "FEATURE_BUILD":
        symbol = payload["symbol"]
        if symbol not in PROTOCOL["symbols"]:
            raise ValueError("unsupported daily development instrument")
        frame, receipt = verified_history(repository / "data/history/yahoo_daily", symbol)
        if len(frame) > 50000:
            raise ValueError("feature input row budget exceeded")
        data = build_dataset(frame)
        path = directory / "dataset.csv"
        data.to_csv(path, index=False, lineterminator="\n")
        version = digest(path.read_bytes())
        return {"status": "SUCCEEDED", "symbol": symbol, "dataset_path": str(path), "dataset_sha256": version,
                "source_raw_sha256": receipt["raw_sha256"], "source_normalized_sha256": receipt["normalized_sha256"],
                "rows": len(data), "first": data.date.min(), "last": data.date.max(), "protocol": PROTOCOL,
                "feature_availability": "prior completed daily bars only; bar-end lower-bound provenance"}
    if kind == "HISTORICAL_BACKTEST":
        if payload.get("scope") == "raw_futures":
            from ..instruments import get_instrument
            from .contract_replay import load_contract_receipts
            history = load_contract_receipts(repository / "data/licensed/databento", get_instrument("NQ"), "NQZ6")
            return {"status": "BLOCKED", "reason": "AUTHENTIC_CONTRACT_HISTORY_REQUIRED" if history["status"] == "DATA_BLOCKED" else "RECEIPTS_REQUIRE_PIT_CALENDAR_REVIEW",
                    "licensed_rows": len(history["bars"]), "strategies": ["orb", "vwap", "value"], "performance": None}
        data, source = dataset_from(store, job)
        result = context_backtest(data)
        write_json(directory / "backtest.json", result)
        return {"status": "SUCCEEDED", "symbol": source["symbol"], "dataset_sha256": source["dataset_sha256"], "report": result}
    if kind == "WALK_FORWARD_VALIDATION":
        data, source = dataset_from(store, job)
        parts = folds(data)
        if not parts:
            return {"status": "BLOCKED", "reason": "INSUFFICIENT_GROUPS"}
        return {"status": "SUCCEEDED", "folds": len(parts), "dataset_sha256": source["dataset_sha256"],
                "protocol": PROTOCOL, "holdout_scored": False}
    if kind == "MODEL_TRAINING":
        data, source = dataset_from(store, job)
        code_paths = ("src/nocturne/research/daily_experiment.py", "src/nocturne/research/validation.py", "src/nocturne/ml/calibration.py")
        sources = {p: (repository / p).read_bytes() for p in code_paths}
        code = b"".join(sources.values())
        import sklearn
        experiment = digest(canonical({"dataset": source["dataset_sha256"], "protocol": PROTOCOL,
                                       "code_sha256": digest(code), "sklearn": sklearn.__version__}))
        destination = store.root / "experiments" / experiment
        receipt = destination / "training.json"
        if receipt.exists():
            result = json.loads(receipt.read_text())
            for entry in result["splits"]:
                if digest((destination / f"fold_{entry['fold']}.joblib").read_bytes()) != entry["model_sha256"]:
                    raise ValueError("cached challenger artifact corrupted")
            return {**result, "reused_without_retraining": True}
        if destination.exists():
            return {"status": "BLOCKED", "reason": "INCOMPLETE_EXPERIMENT_REQUIRES_OPERATOR_REVIEW", "experiment_id": experiment}
        destination.parent.mkdir(parents=True, exist_ok=True)
        splits = train_development(data, destination)
        for name, content in sources.items():
            snapshot = destination / "source" / name
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(content)
        result = {"status": "SUCCEEDED", "experiment_id": experiment, "symbol": source["symbol"],
                  "dataset_sha256": source["dataset_sha256"], "destination": str(destination), "splits": splits,
                  "model_version": "logistic-development-v1", "code_sha256": digest(code),
                  "decision": "NO_PROMOTION", "reused_without_retraining": False}
        write_json(receipt, result)
        return result
    if kind == "MODEL_EVALUATION":
        data, source = dataset_from(store, job)
        trained = ancestor(store, job, "MODEL_TRAINING")
        destination = Path(trained["destination"])
        cached = destination / "evaluation.json"
        if cached.exists():
            result = json.loads(cached.read_text())
            if digest((destination / "predictions.csv").read_bytes()) != result["predictions_sha256"]:
                raise ValueError("cached predictions changed")
            return {**result, "reused_without_rescoring": True}
        report, predictions = evaluate_development(data, destination, trained["splits"])
        predictions.to_csv(destination / "predictions.csv", index=False, lineterminator="\n")
        result = {"status": "SUCCEEDED", "experiment_id": trained["experiment_id"], "symbol": source["symbol"],
                  "dataset_sha256": source["dataset_sha256"], "evaluation": report,
                  "predictions_sha256": digest((destination / "predictions.csv").read_bytes()),
                  "reused_without_rescoring": False}
        delta = report["metrics"]["p_model"]["brier"] - report["metrics"]["p_frequency"]["brier"]
        result["brier_delta"] = delta
        result["finding"] = "REJECT_INCREMENTAL_CLAIM" if delta >= 0 else "SMALL_DEVELOPMENT_DIFFERENCE_REQUIRES_INDEPENDENT_VALIDATION"
        write_json(cached, result)
        return result
    if kind == "RESEARCH_REPORT":
        jobs = store.jobs()
        # The report cannot include its own final state until it has committed.
        # Omit itself instead of publishing a misleading permanent RUNNING job.
        jobs = [entry for entry in jobs if entry["id"] != job["id"]]
        # A report is a snapshot of all job states, not a dependency of inference.
        from datetime import datetime, timezone
        from collections import Counter
        audit_path = repository / "reports/phase3l_forward_audit.json"
        audit = json.loads(audit_path.read_text()) if audit_path.exists() else None
        import os
        from ..ml.status import governance
        report = {"generated_at": datetime.now(timezone.utc).isoformat(), "state_counts": dict(Counter(j["state"] for j in jobs)),
                  "job_events": store.events(),
                  "jobs": [{**j, "payload": json.loads(j["payload"]), "dependencies": json.loads(j["dependencies"]),
                            "result": json.loads(j["result"]) if j["result"] else None} for j in jobs],
                  "forward_audit_snapshot": audit, "historical_and_forward_metrics_separate": True,
                  "credential_presence": {name: bool(os.environ.get(name)) for name in ("DATABENTO_API_KEY", "FRED_API_KEY", "BLS_API_KEY", "NASDAQ_DATA_LINK_API_KEY")},
                  "model_governance": governance(),
                  "provider_health_scope": "credential presence and completed source-validation jobs; not an entitlement or uptime certification",
                  "promotion": "NO_PROMOTION", "trading_decision": "NO_TRADE",
                  "limits": "single awake host; research-only daily context; no futures entitlement or independent PIT history"}
        write_json(directory / "research_report.json", report)
        lines = ["# Research job snapshot", "", f"Generated: {report['generated_at']}", "",
                 f"States: {report['state_counts']}", "", "Trading: NO_TRADE. No automatic promotions.", "",
                 "Daily index diagnostics are not futures strategy P&L or independent validation.", ""]
        for entry in jobs:
            lines.append(f"- `{entry['kind']}` ({entry['lane']}): **{entry['state']}** — `{entry['id']}`")
            result = json.loads(entry["result"]) if entry["result"] else {}
            if not result:
                continue
            if result.get("reason"):
                lines.append(f"  Reason: {result['reason']}")
            if result.get("evaluation"):
                for model, metrics in result["evaluation"]["metrics"].items():
                    lines.append(f"  {result['symbol']} {model}: n={metrics['n']}, Brier={metrics['brier']}, AUC={metrics['auc']:.5f}; development diagnostic only.")
            if result.get("report", {}).get("sensitivity"):
                summary = result["report"]["sensitivity"]["2"]
                lines.append(f"  {result['symbol']} index-only, 2-bp hypothetical cost: n={summary['observations']}, "
                             f"mean fraction={summary['net_mean_fraction']:.8f}, profit factor={summary['profit_factor']:.5f}; not futures P&L.")
            if result.get("coverage"):
                for source in result["coverage"]:
                    lines.append(f"  {source['symbol']}: {source['rows']} rows, {source['first']} through {source['last']}, {source['kind']}.")
        (directory / "research_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        return {"status": "SUCCEEDED", "report_path": str(directory / "research_report.json"), "markdown_path": str(directory / "research_report.md")}
    raise ValueError("no job handler")
