"""Small receipt-to-existing-engine diagnostic, not a promotion experiment."""
from dataclasses import asdict
from pathlib import Path
import math

import pandas as pd

from ..instruments import get_instrument
from ..adapters.snapshots import canonical, digest
from ..auction.session import session_bars
from ..market_clock import session_window
from ..backtest.data import add_session_column
from ..backtest.study import _signals, _run
from ..backtest.engine import BacktestConfig, BacktestReport
from .contract_replay import load_contract_receipts
from .target_dataset import TargetDatasetConfig, build_strategy_target_dataset


def pilot_summary(report):
    result = report.summary()
    if not math.isfinite(result["profit_factor"]):
        result["profit_factor"] = None
        result["profit_factor_status"] = "UNDEFINED_NO_LOSSES"
    return result


def run_pilot(root, instrument, contract, destination):
    spec = get_instrument(instrument)
    history = load_contract_receipts(root, spec, contract)
    result = {"status": "BLOCKED", "instrument": instrument, "contract": contract,
              "bar_interval": "1min", "protocol_version": "pilot-full-TP1-cashflow-v2",
              "engine_code_sha256": digest((Path(__file__).resolve().parents[1] / "backtest/engine.py").read_bytes()),
              "licensed_rows": len(history["bars"]), "directional_metrics": None,
              "target_first_probability": None, "survival_fit": None,
              "decision": "NO_PROMOTION", "trading_decision": "NO_TRADE"}
    if history["status"] == "DATA_BLOCKED":
        return {**result, "reason": "AUTHENTIC_CONTRACT_HISTORY_REQUIRED"}
    if len(history["bars"]) > 10000:
        return {**result, "reason": "BOUNDED_PILOT_ROW_BUDGET_EXCEEDED"}
    bars = add_session_column(history["bars"], spec)
    days = sorted(bars.session.unique())
    complete = []
    gaps = {}
    for day in days:
        rth = session_bars(bars, spec, "RTH", day)
        if rth.empty:
            continue
        window = session_window(spec, "RTH", day)
        grid = pd.date_range(window.start_utc, window.end_utc, freq="1min", inclusive="left")
        absent = len(grid.difference(pd.DatetimeIndex(rth.timestamp)))
        gaps[str(day)] = absent
        if absent == 0 and len(rth) == len(grid):
            complete.append(day)
    result.update(source_inventory_sha256=history["inventory_sha256"], receipts=history["receipts"],
                  missing_rth_minutes=gaps, pit_status=history["pit_status"],
                  calendar_basis="existing bounded engineering calendar, not new provider-authoritative evidence")
    if not complete:
        return {**result, "reason": "NO_COMPLETE_RTH_MINUTE_GRID"}
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    strategy_results = {}
    for name in ("orb", "vwap"):
        signals = _signals(name, bars, spec, complete)
        # One whole contract, one full TP1 exit: never present a fractional
        # half-contract scale-out as an executable futures fill.
        reports = {str(slip): _run(bars, spec, complete, signals,
                   BacktestConfig(slippage_ticks=slip, exit_schedule=((0, 1.),),
                                  move_stop_to_breakeven_after_tp1=False, cost_model="cashflow-v2")) for slip in (1, 3, 4)}
        trades = reports["1"].trades
        labels = []
        for day in complete:
            rth = session_bars(bars, spec, "RTH", day)
            built = build_strategy_target_dataset(signals.get(day, []), rth, spec,
                        TargetDatasetConfig(horizon_bars=60, interval="1min", slippage_ticks=1.))
            if not built.empty:
                built["contract_id"] = contract
                built["source_inventory_sha256"] = history["inventory_sha256"]
                built["session"] = "RTH"
                built["regime"] = "UNCLASSIFIED"
                built["volatility_context"] = None
                built["trade_profile_context"] = None
                built["orderflow_context"] = None
                built["signal_id"] = contract + "|" + built.signal_id.astype(str)
                built["pit_status"] = history["pit_status"]
                built["target_first_probability"] = None
                labels.append(built)
        paths = []
        if labels:
            path = destination / f"{contract}_{name}_labels.csv"
            pd.concat(labels, ignore_index=True).to_csv(path, index=False, lineterminator="\n")
            paths.append({"path": str(path), "sha256": digest(path.read_bytes())})
        serialized = [{**asdict(trade), "regime": "UNCLASSIFIED"} for trade in trades]
        winners, losers = [t.dollars for t in trades if t.dollars > 0], [t.dollars for t in trades if t.dollars <= 0]
        strategy_results[name] = {"cost_sensitivity": {cost: pilot_summary(report) for cost, report in reports.items()},
                                 "trades": serialized, "average_win_dollars": sum(winners) / len(winners) if winners else None,
                                 "average_loss_dollars": sum(losers) / len(losers) if losers else None,
                                 "by_year": {str(year): pilot_summary(BacktestReport([t for t in trades if t.entry_time.year == year])) for year in sorted({t.entry_time.year for t in trades})},
                                 "labels": paths, "target_label_horizon": "60 completed minute bars; not strategy exit horizon",
                                 "label_rows": sum(len(frame) for frame in labels)}
    return {**result, "status": "SUCCEEDED", "scope": "PILOT_PLUMBING_DIAGNOSTIC_ONLY_NOT_INDEPENDENT_VALIDATION",
            "strategies": strategy_results, "completed_sessions": [str(d) for d in complete],
            "blocked_families": ["trade-derived value profile", "genuine CVD/quote/depth", "PIT macro volatility expansion"],
            "fill_policy": "existing next-bar entry, stop-first same-bar ambiguity and configured slippage/commission; not queue simulation",
            "position_policy": "one contract; full TP1 exit; no fractional scale-out or breakeven move",
            "cost_validation": "cashflow-v2 analytically checked; one entry/exit slip in fill P&L, two commission sides per contract. Execution realism remains unvalidated",
            "excursion_definition": "full-bar extremes including exit bar; bounds, not reconstructed intrabar execution-path MFE/MAE",
            "vwap_definition": "existing typical-price OHLCV proxy, not authentic trade-derived VWAP"}
