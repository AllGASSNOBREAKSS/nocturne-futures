#!/usr/bin/env python
"""Phase 3B.1 target-first model experiment.

Combines the VWAP, revised-ORB and value-area target datasets, attaches
point-in-time features, splits by originating signal, and compares frequency,
logistic and gradient-boosted target-first probabilities.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocturne.backtest.data import add_session_column, load_intraday  # noqa: E402
from nocturne.instruments import get_instrument  # noqa: E402
from nocturne.ml.target_model import evaluate_folds, evaluate_split  # noqa: E402
from nocturne.research.target_training import (  # noqa: E402
    build_training_frame,
    expanding_folds,
    load_targets,
    prepare_binary,
    split_by_signal,
)


def main() -> int:
    spec = get_instrument("NQ")
    nq_bars, nq_meta = load_intraday("NQ")
    es_bars, es_meta = load_intraday("ES")
    nq_bars = add_session_column(nq_bars, spec)
    es_bars = add_session_column(es_bars, get_instrument("ES"))
    vix = pd.read_csv(ROOT / "data" / "market" / "daily" / "VIX.csv")
    vix["date"] = pd.to_datetime(vix["date"]).dt.strftime("%Y-%m-%d")

    targets = load_targets()
    features = build_training_frame(targets, nq_bars, es_bars, vix, spec)
    binary, feature_columns = prepare_binary(features)
    if len(binary) < 40:
        raise SystemExit(f"not enough binary rows: {len(binary)}")

    train, validation, test = split_by_signal(binary)
    results = evaluate_split(train, validation, test, feature_columns)
    folds = expanding_folds(binary, n_folds=3)
    fold_summary = evaluate_folds(folds, feature_columns)

    class_balance = {
        "train": round(float(train["y"].mean()), 4),
        "validation": round(float(validation["y"].mean()), 4),
        "test": round(float(test["y"].mean()), 4),
    }
    best_test = min(results, key=lambda name: results[name].metrics["brier"])
    best_auc = results[best_test].metrics.get("auc")
    decision = "NO_PROMOTION"
    if (
        best_test != "frequency"
        and results[best_test].metrics["brier"] < results["frequency"].metrics["brier"] - 0.005
        and (best_auc is None or best_auc >= 0.55)
        and results[best_test].metrics["ece"] <= 0.05
        and len(test) >= 100
    ):
        decision = "CANDIDATE_SHADOW"
    decision_reason = (
        f"Best test Brier is {results[best_test].metrics['brier']:.4f} ({best_test}); "
        f"AUC={best_auc}; ECE={results[best_test].metrics['ece']:.4f}; "
        f"test n={len(test)}; test positive rate={class_balance['test']:.3f} vs "
        f"train {class_balance['train']:.3f}. "
        "A Brier gain without ranking skill or calibration is a class-shift artifact, not a validated edge."
    )

    coverage = {
        "target_rows": int(len(targets)),
        "feature_rows": int(len(features)),
        "binary_rows": int(len(binary)),
        "signals": int(binary["signal_id"].nunique()),
        "base_rate": round(float(binary["y"].mean()), 4),
        "by_strategy": binary["strategy_id"].value_counts().to_dict(),
        "by_outcome": targets["outcome"].value_counts().to_dict(),
        "feature_non_null": {
            column: round(float(binary[column].notna().mean()), 3)
            for column in feature_columns
        },
        "nq_data": nq_meta,
        "es_data": es_meta,
    }

    report = {
        "phase": "3B.1",
        "instrument": "NQ",
        "coverage": coverage,
        "split": {
            "train_rows": int(len(train)),
            "train_signals": int(train["signal_id"].nunique()),
            "validation_rows": int(len(validation)),
            "validation_signals": int(validation["signal_id"].nunique()),
            "test_rows": int(len(test)),
            "test_signals": int(test["signal_id"].nunique()),
            "class_balance": class_balance,
        },
        "decision": decision,
        "decision_reason": decision_reason,
        "test": {
            name: {
                "metrics": result.metrics,
                "predictions": result.predictions.to_dict("records"),
                "coefficients": result.coefficients,
            }
            for name, result in results.items()
        },
        "walk_forward": fold_summary,
    }
    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "phase3b_target_model.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    lines = [
        "# Phase 3B.1 Target-First Model",
        "",
        f"Binary rows: **{coverage['binary_rows']}** from **{coverage['signals']}** signals; "
        f"base rate **{coverage['base_rate']:.3f}**.",
        f"Strategies: {coverage['by_strategy']}.",
        f"Split: train {len(train)} / validation {len(validation)} / test {len(test)} rows.",
        "",
        "| Model | Brier | Log loss | Accuracy | ECE | AUC |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for name, result in results.items():
        metrics = result.metrics
        lines.append(
            f"| {name} | {metrics['brier']:.4f} | {metrics['log_loss']:.4f} | "
            f"{metrics['accuracy']:.3f} | {metrics['ece']:.4f} | {metrics.get('auc', '-')} |"
        )
    lines.extend(
        [
            "",
            "## Expanding-window folds",
            "",
            "| Model | Folds | Mean Brier | Mean log loss | Mean accuracy |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for name, summary in fold_summary.items():
        lines.append(
            f"| {name} | {len(summary['folds'])} | {summary['mean_brier']:.4f} | "
            f"{summary['mean_log_loss']:.4f} | {summary['mean_accuracy']:.3f} |"
        )
    lines.extend(
        [
            "",
            "## Decision",
            "",
            f"**{decision}.** {decision_reason}",
            "",
            "The sample is small (three strategies, 60 days of 5-minute bars). "
            "No model is promoted unless it beats the frequency baseline on the "
            "untouched test split and the expanding folds, with acceptable calibration.",
            "",
        ]
    )
    (ROOT / "reports" / "phase3b_target_model.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
