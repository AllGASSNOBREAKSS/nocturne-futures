"""Run the pre-registered Phase 3U free-data walk-forward backtest on ^NDX.

Outputs (content-addressed by data + code + protocol fingerprint):
  data/studies/phase3u/<fingerprint>/predictions.csv
  reports/phase3u_backtest.json and reports/phase3u_backtest.md
An unchanged fingerprint reuses the stored result instead of re-scoring.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from nocturne.collector.store import Archive
from nocturne.research import free_data_experiment as fx
from nocturne.research.daily_experiment import verified_history

ROOT = Path(__file__).resolve().parents[1]


def fmt(value, digits=4):
    return "n/a" if value is None else f"{value:.{digits}f}"


def markdown(report):
    r, prim = report["results"], f"C{fx.PROTOCOL['primary_C']}_wall"
    lines = ["# Phase 3U — free-data walk-forward backtest (^NDX, index-level)", "",
             f"Generated {report['generated_at']}. Fingerprint `{report['fingerprint'][:16]}`.",
             "Scope: Nasdaq-100 cash index research forecasts. **Not NQ futures, not order flow, not executable P&L.**",
             f"Sample: {report['dataset']['test_rows']} test sessions, {report['dataset']['first_test']} to "
             f"{report['dataset']['last_test']}; annual expanding refits, 5-day embargo.", "",
             f"**Verdicts:** direction `{r['verdicts']['direction_free_features']}`, range `{r['verdicts']['range_free_features']}`. "
             "NO_PROMOTION / NO_TRADE.", "", "## Direction (next session close > open)", "",
             "| Era | Model | n | AUC | Bal. acc | Brier | Log loss |", "|---|---|---|---|---|---|---|"]
    for era in ("development", "exposed", "all"):
        for label, key in (("frequency", "p_frequency"), ("base logistic", f"p_base_{prim}"), ("free-data logistic", f"p_free_{prim}")):
            m = r["direction"][era][key]
            lines.append(f"| {era} | {label} | {m['n']} | {fmt(m['auc'])} | {fmt(m['balanced_accuracy'])} | {fmt(m['brier'], 5)} | {fmt(m['log_loss'], 5)} |")
    lines += ["", "Brier differences (negative = first model better), 95% monthly block-bootstrap CI:", ""]
    for era in ("development", "exposed"):
        for name, v in r["comparisons"][era].items():
            lines.append(f"- {era} `{name}`: {v['mean']:+.6f} [{v['ci95'][0]:+.6f}, {v['ci95'][1]:+.6f}]")
    lines += ["", "## Next-session range quantiles ((high-low)/close)", "",
              "| Era | Model | P50 cov | P80 cov | P90 cov | Mean pinball |", "|---|---|---|---|---|---|"]
    for era in ("development", "exposed", "all"):
        for name, m in r["range"][era].items():
            lines.append(f"| {era} | {name} | {fmt(m['q50']['coverage'])} | {fmt(m['q80']['coverage'])} | {fmt(m['q90']['coverage'])} | {fmt(m['mean_pinball'], 6)} |")
    lines += ["", "## Training-window sensitivity (all test years, Brier / AUC)", ""]
    for key, m in sorted(r["direction"]["all"].items()):
        lines.append(f"- `{key}`: Brier {fmt(m['brier'], 5)}, AUC {fmt(m['auc'])}")
    lines += ["", "## Year by year (Brier: frequency / base / free; mean pinball: trailing / base / free)", "",
              "| Year | n | Brier freq | Brier base | Brier free | AUC free | Pinball trail | Pinball base | Pinball free | Free P80 cov |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for year, v in r["by_year"].items():
        d, p = v["direction"], v["range_mean_pinball"]
        lines.append(f"| {year} | {v['n']} | {fmt(d['p_frequency']['brier'], 5)} | {fmt(d[f'p_base_{prim}']['brier'], 5)} | "
                     f"{fmt(d[f'p_free_{prim}']['brier'], 5)} | {fmt(d[f'p_free_{prim}']['auc'])} | {fmt(p['trailing'], 6)} | "
                     f"{fmt(p['base'], 6)} | {fmt(p['free'], 6)} | {fmt(v['free_q80_coverage'])} |")
    lines += ["", "## Regimes", "", "| Regime | n | AUC free | Brier freq | Brier free | Pinball trail | Pinball free |", "|---|---|---|---|---|---|---|"]
    for name, v in r["regimes"].items():
        d, p = v["direction"], v["range_mean_pinball"]
        lines.append(f"| {name} | {v['n']} | {fmt(d[f'p_free_{prim}']['auc'])} | {fmt(d['p_frequency']['brier'], 5)} | "
                     f"{fmt(d[f'p_free_{prim}']['brier'], 5)} | {fmt(p['trailing'], 6)} | {fmt(p['free'], 6)} |")
    lines += ["", "## Hypothetical index exposure (sign of free-model probability, 0.02 dead zone)", "",
              "Open-to-close index fractions, costs in basis points per trade. **Not NQ P&L; not executable.**", "",
              "| Era | Rule | Cost | Trades | Win rate | Expectancy | Profit factor | Total return | Max DD |", "|---|---|---|---|---|---|---|---|---|"]
    for era in ("development", "exposed"):
        for rule, costs in r["strategy"][era].items():
            for cost, m in costs.items():
                lines.append(f"| {era} | {rule} | {cost} | {m['trades']} | {fmt(m['win_rate'])} | {fmt(m['net_expectancy_fraction'], 6)} | "
                             f"{fmt(m['profit_factor'])} | {fmt(m['total_return_fraction'])} | {fmt(m['max_drawdown_fraction'])} |")
    lines += ["", "## Point-in-time join audit", ""]
    for name, a in report["pit_audit"].items():
        lines.append(f"- {name}: {a}")
    lines += ["", "## Limitations", ""] + [f"- {x}" for x in report["limitations"]]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--free-root", type=Path, default=ROOT / "data/history/free")
    parser.add_argument("--force", action="store_true", help="re-score even if the fingerprint exists")
    parser.add_argument("--report-dir", type=Path, default=ROOT / "reports")
    parser.add_argument("--study-root", type=Path, default=ROOT / "data/studies/phase3u")
    args = parser.parse_args()
    archive = Archive(args.free_root)
    frame, receipt = verified_history(ROOT / "data/history/yahoo_daily", fx.PROTOCOL["symbol"])
    code = b"".join((ROOT / p).read_bytes() for p in ("src/nocturne/research/free_data_experiment.py",
                                                      "src/nocturne/research/daily_experiment.py",
                                                      "src/nocturne/ml/calibration.py", "scripts/phase3u_backtest.py"))
    fingerprint, inputs = fx.fingerprint(archive, code, receipt["raw_sha256"])
    study = args.study_root / fingerprint[:24]
    cached = study / "report.json"
    if cached.exists() and not args.force:
        report = json.loads(cached.read_text()) | {"reused": True}
        args.report_dir.mkdir(parents=True, exist_ok=True)
        (args.report_dir / "phase3u_backtest.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps({"reused": True, "verdicts": report["results"]["verdicts"]}))
        return 0
    data, audit = fx.build(frame, archive)
    predictions, folds = fx.run(data)
    results = fx.evaluate(predictions)
    study.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(study / "predictions.csv", index=False, lineterminator="\n")
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "fingerprint": fingerprint, "inputs": inputs,
              "protocol": fx.PROTOCOL, "features": {"base": fx.BASE, "free": fx.FREE},
              "dataset": {"instrument": "^NDX cash index (Yahoo research-grade, frozen, checksum-verified)",
                          "history_rows": len(frame), "history_first": str(frame.date.min()), "history_last": str(frame.date.max()),
                          "modelling_rows": len(data), "test_rows": len(predictions),
                          "first_test": str(predictions.date.min()), "last_test": str(predictions.date.max())},
              "folds": folds, "pit_audit": audit, "results": results,
              "predictions_path": str(study / "predictions.csv"),
              "predictions_sha256": hashlib.sha256((study / "predictions.csv").read_bytes()).hexdigest(),
              "limitations": ["Cash index, not NQ/ES contracts; no roll, no futures session, no order flow.",
                              "FRED/CFTC values are latest vintages; daily market series are rarely revised, revisable macro series are excluded.",
                              "Conservative availability lags reduce, but cannot prove absence of, publication-time error.",
                              "SEC ticker set is today's megacaps (survivorship-biased membership).",
                              "2024+ was examined by earlier phases with other features; it is not an untouched holdout.",
                              "Hypothetical index exposure ignores financing, futures basis and realistic execution."],
              "promotion": "NO_PROMOTION", "trading_decision": "NO_TRADE", "futures_status": "FUTURES_DATA_BLOCKED"}
    cached.write_text(json.dumps(report, indent=2, default=str) + "\n")
    args.report_dir.mkdir(parents=True, exist_ok=True)
    (args.report_dir / "phase3u_backtest.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    (args.report_dir / "phase3u_backtest.md").write_text(markdown(report), encoding="utf-8")
    print(json.dumps({"reused": False, "test_rows": len(predictions), "verdicts": results["verdicts"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
