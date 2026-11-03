#!/usr/bin/env python
"""Phase 3A ML audit.

Explains why the daily barrier models do or do not beat the frequency baseline:
label geometry, class balance, univariate signal, walk-forward calibration,
regime stability and a simple threshold economic check.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nocturne.ml.baseline import (  # noqa: E402
    FrequencyBaseline,
    GradientBoostedBaseline,
    LogisticBaseline,
)
from nocturne.ml.calibration import classification_metrics  # noqa: E402
from nocturne.pipeline import load_daily_csv  # noqa: E402
from nocturne.research.dataset import binary_sample, build_training_frame  # noqa: E402
from nocturne.research.features import FEATURE_COLUMNS  # noqa: E402
from nocturne.research.walk_forward import walk_forward  # noqa: E402

CONFIGS = {
    "current_t1.5_s1.0_h5": dict(target_atr=1.5, stop_atr=1.0, horizon=5),
    "short_t1.0_s1.0_h3": dict(target_atr=1.0, stop_atr=1.0, horizon=3),
    "tight_stop_t1.0_s0.5_h5": dict(target_atr=1.0, stop_atr=0.5, horizon=5),
    "long_t2.0_s1.0_h10": dict(target_atr=2.0, stop_atr=1.0, horizon=10),
}


def univariate_auc(frame: pd.DataFrame) -> dict[str, float]:
    out = {}
    for feature in FEATURE_COLUMNS:
        try:
            out[feature] = round(float(roc_auc_score(frame["y"], frame[feature])), 4)
        except ValueError:
            continue
    return dict(sorted(out.items(), key=lambda item: abs(item[1] - 0.5), reverse=True))


def economic_check(frame: pd.DataFrame, predictions: pd.DataFrame, threshold: float) -> dict:
    indexed = frame.set_index("signal_index")
    trades = predictions[predictions["p"] >= threshold].copy()
    if trades.empty:
        return {"threshold": threshold, "trades": 0}
    trades["entry"] = trades["index"].map(indexed["entry_price"])
    trades["stop"] = trades["index"].map(indexed["stop"])
    trades["exit"] = trades["index"].map(indexed["exit_price"])
    trades["risk"] = trades["entry"] - trades["stop"]
    trades["r"] = (trades["exit"] - trades["entry"]) / trades["risk"]
    cost_dollars = 15.0  # $5 commission round trip + 2 ticks NQ slippage
    trades["dollars"] = trades["r"] * trades["risk"] * 20.0 - cost_dollars
    equity = trades["dollars"].cumsum()
    drawdown = (equity.cummax() - equity).max()
    return {
        "threshold": threshold,
        "trades": int(len(trades)),
        "win_rate": round(float((trades["dollars"] > 0).mean()), 4),
        "avg_r": round(float(trades["r"].mean()), 4),
        "net_dollars": round(float(trades["dollars"].sum()), 2),
        "expectancy_dollars": round(float(trades["dollars"].mean()), 2),
        "max_drawdown_dollars": round(float(drawdown), 2),
    }


def stability(frame: pd.DataFrame, predictions: pd.DataFrame) -> dict:
    indexed = frame.set_index("signal_index")
    preds = predictions.copy()
    preds["atr_pct"] = preds["index"].map(indexed["atr_pct"])
    median = preds["atr_pct"].median()
    out = {}
    for name, mask in (
        ("low_vol", preds["atr_pct"] <= median),
        ("high_vol", preds["atr_pct"] > median),
    ):
        subset = preds[mask]
        if len(subset) and subset["y"].nunique() == 2:
            out[name] = classification_metrics(subset["y"].to_numpy(), subset["p"].to_numpy())
    for year, group in preds.groupby(preds["date"].str[:4]):
        if group["y"].nunique() == 2:
            out[f"year_{year}"] = classification_metrics(group["y"].to_numpy(), group["p"].to_numpy())
    return out


def main() -> int:
    bars = load_daily_csv("NQ")
    report: dict = {"instrument": "NQ", "bars": len(bars), "configs": {}}
    markdown = ["# NQ ML Audit", "", f"Bars: {len(bars)}", ""]

    for name, params in CONFIGS.items():
        frame = build_training_frame(bars, **params)
        binary = binary_sample(frame)
        if len(binary) < 900:
            continue
        counts = frame["outcome"].value_counts().to_dict()
        leakage = {
            "entry_is_next_bar": bool((frame["entry_index"] == frame["signal_index"] + 1).all()),
            "exit_after_entry": bool((frame["exit_index"] >= frame["entry_index"]).all()),
        }
        entry = {
            "params": params,
            "outcomes": counts,
            "binary_n": int(len(binary)),
            "base_rate": round(float(binary["y"].mean()), 4),
            "univariate_auc": univariate_auc(binary),
            "leakage": leakage,
            "models": {},
        }
        markdown.append(
            f"## {name}\n\nTP {counts.get('TP_FIRST', 0)} | SL {counts.get('SL_FIRST', 0)} | "
            f"timeout {counts.get('TIMEOUT', 0)} | ambiguous {counts.get('AMBIGUOUS', 0)} | "
            f"binary n {len(binary)} | base rate {entry['base_rate']:.3f}\n"
        )
        markdown.append("| Model | Brier | Log loss | Acc | ECE |")
        markdown.append("|---|---:|---:|---:|---:|")

        factories = [("frequency", FrequencyBaseline), ("logistic", LogisticBaseline)]
        if name == "current_t1.5_s1.0_h5":
            factories.append(("gbm", lambda: GradientBoostedBaseline(max_iter=50)))
        for model_name, factory in factories:
            try:
                result = walk_forward(
                    frame,
                    model_factory=factory,
                    model_name=model_name,
                    min_train=750,
                    step=21,
                )
            except Exception as exc:  # noqa: BLE001
                entry["models"][model_name] = {"error": str(exc)}
                continue
            entry["models"][model_name] = {
                "metrics": result.metrics,
                "predictions_n": int(len(result.predictions)),
            }
            metrics = result.metrics
            markdown.append(
                f"| {model_name} | {metrics['brier']:.4f} | {metrics['log_loss']:.4f} | "
                f"{metrics['accuracy']:.3f} | {metrics['ece']:.4f} |"
            )
            if model_name == "logistic":
                entry["stability"] = stability(frame, result.predictions)
                entry["economic"] = [
                    economic_check(frame, result.predictions, threshold)
                    for threshold in (0.50, 0.55, 0.60)
                ]
        if entry.get("stability"):
            markdown.append("\n### Regime stability (logistic)\n")
            markdown.append("| Regime | n | Brier | Acc | ECE |")
            markdown.append("|---|---:|---:|---:|---:|")
            for regime, metrics in entry["stability"].items():
                markdown.append(
                    f"| {regime} | {metrics['n']} | {metrics['brier']:.4f} | "
                    f"{metrics['accuracy']:.3f} | {metrics['ece']:.4f} |"
                )
        if entry.get("economic"):
            markdown.append("\n### Threshold economic check (logistic, $15 round trip)\n")
            markdown.append("| Threshold | Trades | Win % | Avg R | Net $ | Max DD $ |")
            markdown.append("|---:|---:|---:|---:|---:|---:|")
            for item in entry["economic"]:
                if item.get("trades", 0) == 0:
                    markdown.append(f"| {item['threshold']:.2f} | 0 | - | - | - | - |")
                    continue
                markdown.append(
                    f"| {item['threshold']:.2f} | {item['trades']} | "
                    f"{100 * item['win_rate']:.1f} | {item['avg_r']:.3f} | "
                    f"{item['net_dollars']:.2f} | {item['max_drawdown_dollars']:.2f} |"
                )
        markdown.append("")
        report["configs"][name] = entry

    (ROOT / "reports").mkdir(exist_ok=True)
    (ROOT / "reports" / "ml_audit_NQ.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    (ROOT / "reports" / "ml_audit_NQ.md").write_text(
        "\n".join(markdown) + "\n", encoding="utf-8"
    )
    print("\n".join(markdown))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
