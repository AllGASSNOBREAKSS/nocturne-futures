"""Existing strategy families on development-only data with regime/cost audit."""
from dataclasses import asdict
import json
import math
from pathlib import Path

import pandas as pd

from nocturne.backtest.data import load_intraday, add_session_column
from nocturne.backtest.study import _signals, _run
from nocturne.backtest.engine import BacktestConfig, BacktestReport
from nocturne.instruments import get_instrument
from nocturne.research.validation import block_mean_interval

ROOT = Path(__file__).resolve().parents[1]
REGIME_BARS = 1200


def finite(value):
    if isinstance(value, dict):
        return {k: finite(v) for k, v in value.items()}
    if isinstance(value, list):
        return [finite(v) for v in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _regime(frame):
    """The existing rule state using only trailing rows; no transition resampling.

    This reuses regime._label rather than classify_regime so the per-trade audit
    does not repeatedly rescan 1,200 histories. It does not populate future
    transition probabilities.
    """
    from nocturne.regime import _label

    label, adx, efficiency, overlap, vol_percentile, atr = _label(frame)
    return {"label": label, "adx": adx, "efficiency": efficiency, "overlap": overlap,
            "vol_percentile": vol_percentile, "atr": atr}


def main():
    result = {"decision": "NO_PROMOTION", "holdout_scored": False, "instruments": {},
              "limitations": ["retrospective development", "independent strategy ledgers, not joint portfolio",
                              "regimes measured before entry from trailing bars only",
                              "small samples; no regime selection fitted"]}
    for instrument in ("NQ", "ES"):
        bars, meta = load_intraday(instrument)
        spec = get_instrument(instrument)
        bars = add_session_column(bars, spec)
        days = sorted(bars.session.unique())
        days = days[:int(.8 * len(days))]
        bars = bars[bars.session.isin(days)].copy()
        strategies, daily = {}, {}
        for name in ("orb", "vwap", "value"):
            signals = _signals(name, bars, spec, days)
            reports = {str(slip): _run(bars, spec, days, signals, BacktestConfig(slippage_ticks=slip))
                       for slip in (1, 3, 4)}
            report = reports["1"]
            by_regime = {}
            rows = []
            for trade in report.trades:
                history = bars[bars.available_at <= trade.entry_time].tail(REGIME_BARS)
                if len(history) < 80:
                    regime = "UNAVAILABLE"
                else:
                    regime = _regime(history)["label"]
                by_regime.setdefault(regime, []).append(trade)
                rows.append({**asdict(trade), "regime": regime, "day": str(trade.entry_time.date())})
            trades = pd.DataFrame(rows)
            entry = {"costs": {s: r.summary() for s, r in reports.items()},
                     "regimes": {r: BacktestReport(t).summary() for r, t in by_regime.items()},
                     "source": meta}
            if len(trades):
                entry["expectancy_block_interval"] = block_mean_interval(trades.dollars, trades.day)
                daily[name] = trades.groupby("day").dollars.sum()
                trades.to_csv(ROOT / f"reports/phase3e_{instrument}_{name}_trades.csv", index=False)
            strategies[name] = entry
        day_index = [str(d) for d in days]
        pnl = pd.DataFrame(daily).reindex(day_index).fillna(0)
        result["instruments"][instrument] = {"strategies": strategies,
            "daily_pnl_correlation": pnl.corr().to_dict(), "correlation_days": len(pnl),
            "no_signal_day_policy": "zero return; missing market sessions not invented"}
        print(instrument, {n: v["costs"]["1"]["expectancy_dollars"] for n, v in strategies.items()})
    (ROOT / "reports/phase3e_strategies.json").write_text(
        json.dumps(finite(result), indent=2, default=str, allow_nan=False) + "\n")


if __name__ == "__main__":
    main()
