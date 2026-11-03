#!/usr/bin/env python
"""Phase 3B.3 session direction and consolidation experiment."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocturne.backtest.data import add_session_column, load_intraday  # noqa: E402
from nocturne.instruments import get_instrument  # noqa: E402
from nocturne.ml.session_model import evaluate_direction_split  # noqa: E402
from nocturne.ml.target_model import evaluate_split  # noqa: E402
from nocturne.research.session_dataset import (  # noqa: E402
    build_session_dataset,
    prepare_consolidation,
    prepare_direction,
    split_by_day,
)


def main() -> int:
    spec = get_instrument("NQ")
    es_spec = get_instrument("ES")
    nq_bars, nq_meta = load_intraday("NQ")
    es_bars, es_meta = load_intraday("ES")
    nq_bars = add_session_column(nq_bars, spec)
    es_bars = add_session_column(es_bars, es_spec)
    vix = pd.read_csv(ROOT / "data" / "market" / "daily" / "VIX.csv")
    vix["date"] = pd.to_datetime(vix["date"]).dt.strftime("%Y-%m-%d")

    dataset = build_session_dataset(nq_bars, es_bars, vix, spec, es_spec=es_spec)
    if dataset.empty:
        raise SystemExit("no session rows")
    dataset.to_csv(ROOT / "data" / "research" / "session_dataset_NQ.csv", index=False)

    direction, direction_features = prepare_direction(dataset)
    train, validation, test = split_by_day(direction)
    direction_results = evaluate_direction_split(train, validation, test, direction_features)

    consolidation, consolidation_features = prepare_consolidation(dataset)
    ctrain, cvalidation, ctest = split_by_day(consolidation)
    consolidation_results = evaluate_split(ctrain, cvalidation, ctest, consolidation_features)

    coverage = {
        "rows": int(len(dataset)),
        "days": int(dataset["day"].nunique()),
        "sessions": dataset["session"].value_counts().to_dict(),
        "direction": dataset["direction"].value_counts().to_dict(),
        "range_state": dataset["range_state"].value_counts().to_dict(),
        "split": {
            "direction_train": int(len(train)),
            "direction_validation": int(len(validation)),
            "direction_test": int(len(test)),
            "consolidation_train": int(len(ctrain)),
            "consolidation_validation": int(len(cvalidation)),
            "consolidation_test": int(len(ctest)),
        },
        "nq_data": nq_meta,
        "es_data": es_meta,
    }

    best_direction = min(direction_results, key=lambda name: direction_results[name].metrics["log_loss"])
    best_consolidation = min(
        consolidation_results, key=lambda name: consolidation_results[name].metrics["brier"]
    )
    direction_decision = "NO_PROMOTION"
    if (
        best_direction != "frequency"
        and direction_results[best_direction].metrics["log_loss"]
        < direction_results["frequency"].metrics["log_loss"] - 0.01
        and direction_results[best_direction].metrics["accuracy"]
        > direction_results["frequency"].metrics["accuracy"] + 0.05
        and len(test) >= 50
    ):
        direction_decision = "CANDIDATE_SHADOW"

    consolidation_decision = "NO_PROMOTION"
    c_best = consolidation_results[best_consolidation].metrics
    c_freq = consolidation_results["frequency"].metrics
    if (
        best_consolidation != "frequency"
        and c_best["brier"] < c_freq["brier"] - 0.01
        and (c_best.get("auc") or 0) >= 0.55
        and c_best["ece"] <= 0.05
        and len(ctest) >= 50
    ):
        consolidation_decision = "CANDIDATE_SHADOW"

    report = {
        "phase": "3B.3",
        "instrument": "NQ",
        "coverage": coverage,
        "direction": {
            name: {
                "metrics": result.metrics,
                "predictions": result.predictions.to_dict("records"),
            }
            for name, result in direction_results.items()
        },
        "consolidation": {
            name: {
                "metrics": result.metrics,
                "predictions": result.predictions.to_dict("records"),
            }
            for name, result in consolidation_results.items()
        },
        "decisions": {
            "direction": direction_decision,
            "consolidation": consolidation_decision,
            "direction_reason": (
                f"best={best_direction}; test n={len(test)}; "
                f"log_loss={direction_results[best_direction].metrics['log_loss']:.4f}; "
                f"frequency={direction_results['frequency'].metrics['log_loss']:.4f}"
            ),
            "consolidation_reason": (
                f"best={best_consolidation}; test n={len(ctest)}; "
                f"brier={c_best['brier']:.4f}; frequency={c_freq['brier']:.4f}; "
                f"auc={c_best.get('auc')}; ece={c_best['ece']:.4f}"
            ),
        },
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "phase3b3_session_models.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Phase 3B.3 Session Direction and Consolidation",
        "",
        f"Rows: **{coverage['rows']}** across **{coverage['days']}** days.",
        f"Sessions: {coverage['sessions']}.",
        f"Direction labels: {coverage['direction']}.",
        f"Range states: {coverage['range_state']}.",
        f"Split: train {len(train)} / validation {len(validation)} / test {len(test)} rows.",
        "",
        "## Direction (next same session)",
        "",
        "| Model | Log loss | Brier | Accuracy | ECE | BEAR recall | NEUTRAL recall | BULL recall |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, result in direction_results.items():
        metrics = result.metrics
        recalls = metrics["per_class_recall"]
        lines.append(
            f"| {name} | {metrics['log_loss']:.4f} | {metrics['brier']:.4f} | "
            f"{metrics['accuracy']:.3f} | {metrics['ece']:.4f} | "
            f"{recalls['BEAR']} | {recalls['NEUTRAL']} | {recalls['BULL']} |"
        )
    lines.extend(
        [
            "",
            "## Consolidation (next same session range contraction)",
            "",
            "| Model | Brier | Log loss | Accuracy | Precision | Recall | ECE | AUC |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name, result in consolidation_results.items():
        metrics = result.metrics
        lines.append(
            f"| {name} | {metrics['brier']:.4f} | {metrics['log_loss']:.4f} | "
            f"{metrics['accuracy']:.3f} | {metrics['precision']:.3f} | "
            f"{metrics['recall']:.3f} | {metrics['ece']:.4f} | {metrics.get('auc', '-')} |"
        )
    lines.extend(
        [
            "",
            "## Decisions",
            "",
            f"- Direction: **{direction_decision}**. {report['decisions']['direction_reason']}",
            f"- Consolidation: **{consolidation_decision}**. {report['decisions']['consolidation_reason']}",
            "",
            "The sample is 60 days of 5-minute bars. The next-session horizon is long",
            "and overlaps macroeconomic regimes; no result here is a validated edge.",
            "",
        ]
    )
    (ROOT / "reports" / "phase3b3_session_models.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
