"""Fixed sparse development replay; latest 20% of session days excluded."""
import json
from pathlib import Path

import pandas as pd

from nocturne.backtest.data import load_intraday, add_session_column
from nocturne.instruments import get_instrument
from nocturne.forecast.replay import replay_at, save_replay
from nocturne.forecast.monitoring import summarize_evaluations

ROOT = Path(__file__).resolve().parents[1]


def main():
    records, audit = [], []
    for instrument in ("NQ", "ES"):
        bars, meta = load_intraday(instrument)
        spec = get_instrument(instrument)
        bars = add_session_column(bars, spec)
        days = sorted(bars.session.unique())
        development_days = days[:int(len(days) * .8)]
        development = bars[bars.session.isin(development_days)].copy()
        for day in development_days[10::5]:
            asof = pd.Timestamp(str(day) + "T16:00:00Z")
            frozen, outcome = replay_at(development, spec, asof)
            save_replay(ROOT / "data/replay/phase3e", frozen, outcome)
            records.append({"instrument": instrument, "horizon": frozen["forecast"]["forecast_horizon"],
                            "model_version": frozen["version"], "regime": frozen["forecast"]["market_regime"],
                            "outcome": outcome["v1"]})
            for session, item in outcome["bundle"]["outcomes"].items():
                records.append({"instrument": instrument, "horizon": session,
                                "model_version": frozen["version"], "outcome": item})
            audit.append({"replay_id": frozen["replay_id"], "instrument": instrument,
                          "asof": str(asof), "source": meta, "status": outcome["v1"]["status"]})
    report = {"mode": "retrospective_development_only", "holdout_scored": False,
              "selection": "16:00 UTC every fifth development session after ten-session warmup",
              "runs": audit, "monitoring": summarize_evaluations(records)}
    (ROOT / "reports/phase3e_replay.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"replays": len(audit), "v1_matured": sum(x["status"] == "EVALUATED" for x in audit)}))


if __name__ == "__main__":
    main()
