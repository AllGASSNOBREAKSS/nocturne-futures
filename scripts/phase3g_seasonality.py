"""Calendar seasonality with multiple-testing control on decades of daily data."""
import json
from pathlib import Path

from nocturne.adapters.yahoo_history import load_history
from nocturne.research.seasonality import summarize

ROOT = Path(__file__).resolve().parents[1]
DAILY = ROOT / "data/history/yahoo_daily"


def main():
    report = {"decision": "RESEARCH_ONLY", "holdout_scored": False,
              "method": "calendar grouping with year-block 95% intervals and BH-FDR",
              "warning": "seasonality is heavily mined; survivors are hypotheses for "
                         "out-of-sample testing, not signals",
              "instruments": {}}
    for symbol in ("^GSPC", "^NDX", "^VIX", "QQQ"):
        frame = load_history(DAILY, symbol)
        result = summarize(frame)
        report["instruments"][symbol] = result
        survivors = {name: [g["group"] for g in effect["groups"] if g.get("survives_fdr_5pct")]
                     for name, effect in result["effects"].items()}
        print(symbol, result["rows"], result["years"], {k: v for k, v in survivors.items() if v})
    (ROOT / "reports/phase3g_seasonality.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
