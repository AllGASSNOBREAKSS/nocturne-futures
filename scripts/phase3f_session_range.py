"""Session-range coverage diagnostics and bundle metadata (research-only)."""
import json
from pathlib import Path

from nocturne.backtest.data import add_session_column, load_intraday
from nocturne.instruments import get_instrument
from nocturne.research.session_range import session_ranges, summarize

ROOT = Path(__file__).resolve().parents[1]


def main():
    report = {"decision": "NO_PROMOTION", "holdout_scored": False,
              "protocol": "phase3f-session-range-v1",
              "event": "complete analytical session high minus low",
              "methods": "expanding empirical quantiles, no same-day peeking",
              "instruments": {}}
    calibration = {"method": "expanding_empirical_quantiles", "min_history": 20, "instruments": {}}
    for instrument in ("NQ", "ES"):
        bars, meta = load_intraday(instrument)
        spec = get_instrument(instrument)
        bars = add_session_column(bars, spec)
        entry = {"source": meta, "sessions": {}}
        for session in ("ASIA", "LONDON", "NEW_YORK"):
            ranges = session_ranges(bars, spec, session)
            entry["sessions"][session] = summarize(ranges)
        # NEXT_DAY uses the complete RTH window of the next trading day. The
        # distribution is the same complete-window series; only the forecast
        # lead differs, so it is reported as an alias rather than duplicated.
        entry["sessions"]["NEXT_DAY"] = {
            **entry["sessions"]["NEW_YORK"],
            "event": "next_complete_rth_session_high_minus_low",
            "note": "same complete-window distribution with a one-session forecast lead"}
        report["instruments"][instrument] = entry
        calibration["instruments"][instrument] = {
            s: ({"status": data.get("status"),
                 "complete_sessions": data.get("complete_sessions"),
                 "date_range": data.get("date_range"),
                 "coverage": {q: e.get("coverage") for q, e in data.get("expanding_backtest", {}).items()},
                 "n": {q: e.get("n") for q, e in data.get("expanding_backtest", {}).items()}}
                if data.get("status") == "RESEARCH_ONLY" else
                {"status": data.get("status"), "complete_sessions": data.get("complete_sessions")})
            for s, data in entry["sessions"].items()}
        print(instrument, {s: (v.get("complete_sessions"), v.get("expanding_backtest", {}).get("0.8", {}).get("coverage"))
                           for s, v in entry["sessions"].items()})
    (ROOT / "reports/phase3f_session_range.json").write_text(
        json.dumps(report, indent=2, default=lambda x: x.item()) + "\n")
    destination = ROOT / "data/calibration"
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "session_range_calibration.json").write_text(json.dumps(calibration, indent=2) + "\n")


if __name__ == "__main__":
    main()
