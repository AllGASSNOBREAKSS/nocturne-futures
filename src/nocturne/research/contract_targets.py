"""Contract-level target research gate and dataset builder.

Licensed futures research must use one explicit contract at a time. This module
validates contract identity, tick alignment and timestamp availability before
reusing the existing path-dependent target builder. It refuses continuous
proxies, which have no verified roll mapping.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import re

import numpy as np
import pandas as pd

from ..instruments import InstrumentSpec
from ..strategies.base import Signal, TargetSpec
from .target_dataset import TargetDatasetConfig, build_strategy_target_dataset

REQUIRED_COLUMNS = ("timestamp", "available_at", "contract_id",
                    "open", "high", "low", "close", "volume")


@dataclass(frozen=True)
class ContractTargetConfig:
    interval: str = "5min"
    horizon_bars: int = 24
    slippage_ticks: float = 1.0
    commission_per_side: float = 2.5
    tick_tolerance: float = 1e-6
    min_rows: int = 50


@dataclass
class ContractSetup:
    setup_id: str
    contract_id: str
    asof: str
    side: str
    entry: float
    stop: float
    targets: tuple[float, ...]
    strategy_id: str = "contract_research"
    session: str = "UNKNOWN"
    regime: str = "UNKNOWN"
    features: dict = field(default_factory=dict)


def validate_contract_bars(frame: pd.DataFrame, spec: InstrumentSpec,
                           config: ContractTargetConfig | None = None) -> dict:
    config = config or ContractTargetConfig()
    if config.interval not in {"1min", "5min"}:
        raise ValueError("only 1min/5min bars supported")
    missing = set(REQUIRED_COLUMNS) - set(frame)
    if missing:
        raise ValueError(f"missing contract columns: {sorted(missing)}")
    if frame.empty:
        raise ValueError("empty contract frame")
    data = frame.copy()
    for column in ("timestamp", "available_at"):
        data[column] = pd.to_datetime(data[column], utc=True, errors="coerce")
    if data.contract_id.isna().any():
        raise ValueError("contract_id required; continuous proxies are ineligible")
    if not data.contract_id.astype(str).str.fullmatch(re.escape(spec.instrument_id) + r"[HMUZ]\d{1,4}").all():
        raise ValueError("explicit instrument-matched quarterly raw contract required")
    volume = pd.to_numeric(data.volume, errors="coerce")
    if not np.isfinite(volume).all() or (volume < 0).any():
        raise ValueError("invalid volume")
    if data[["timestamp", "available_at"]].isna().any().any():
        raise ValueError("invalid timestamps")
    if data.duplicated(["contract_id", "timestamp"]).any():
        raise ValueError("duplicate contract timestamps")
    prices = data[["open", "high", "low", "close"]].to_numpy(dtype=float)
    if not np.isfinite(prices).all() or (prices <= 0).any():
        raise ValueError("non-positive or non-finite prices")
    if (data.high < data[["open", "close", "low"]].max(axis=1)).any():
        raise ValueError("high below open/close/low")
    if (data.low > data[["open", "close", "high"]].min(axis=1)).any():
        raise ValueError("low above open/close/high")
    if (data.available_at < data.timestamp + pd.Timedelta(config.interval)).any():
        raise ValueError("available_at precedes bar completion")
    ticks = prices / spec.tick_size
    misaligned = int((np.abs(ticks - np.round(ticks)) > config.tick_tolerance).sum())
    if misaligned:
        raise ValueError(f"{misaligned} prices are not aligned to tick size {spec.tick_size}")
    if len(data) < config.min_rows:
        raise ValueError(f"insufficient rows: {len(data)} < {config.min_rows}")
    return {"contracts": sorted(data.contract_id.unique().tolist()), "rows": len(data),
            "first": data.timestamp.min().isoformat(), "last": data.timestamp.max().isoformat(),
            "tick_size": spec.tick_size, "tick_aligned": True,
            "duplicate_timestamps": 0, "interval": config.interval}


def build_contract_targets(frame: pd.DataFrame, spec: InstrumentSpec,
                           setups: list[ContractSetup],
                           config: ContractTargetConfig | None = None) -> pd.DataFrame:
    """Build target-first rows per contract using the existing path logic."""
    config = config or ContractTargetConfig()
    validate_contract_bars(frame, spec, config)
    data = frame.copy()
    for column in ("timestamp", "available_at"):
        data[column] = pd.to_datetime(data[column], utc=True)
    frames = []
    for contract, group in data.groupby("contract_id", sort=True):
        selected = [setup for setup in setups if setup.contract_id == contract]
        ordered = group.sort_values("timestamp")
        for setup in selected:
            side = 1 if setup.side == "LONG" else -1
            if setup.side not in {"LONG", "SHORT"} or pd.Timestamp(setup.asof).tzinfo is None:
                raise ValueError("valid side and timezone-aware setup required")
            if (not setup.targets or not np.isfinite([setup.entry, setup.stop, *setup.targets]).all()
                    or side * (setup.entry - setup.stop) <= 0
                    or any(side * (target - setup.entry) <= 0 for target in setup.targets)):
                raise ValueError("invalid setup geometry")
            signal = Signal(
                strategy_id=setup.strategy_id,
                strategy_version="contract-v1",
                instrument_id=spec.instrument_id,
                asof=pd.Timestamp(setup.asof).to_pydatetime(),
                side=setup.side,
                entry_low=setup.entry,
                entry_high=setup.entry,
                stop=setup.stop,
                targets=tuple(TargetSpec(f"TP{i + 1}", price, abs(price - setup.entry) / abs(setup.entry - setup.stop))
                              for i, price in enumerate(setup.targets)),
                horizon_bars=config.horizon_bars,
                reason_codes=("CONTRACT_RESEARCH",),
            )
            built = build_strategy_target_dataset(
                [signal], ordered, spec,
                TargetDatasetConfig(horizon_bars=config.horizon_bars,
                                    slippage_ticks=config.slippage_ticks,
                                    commission_per_side=config.commission_per_side,
                                    interval=config.interval))
            if built.empty:
                continue
            built["contract_id"] = contract
            built["setup_id"] = setup.setup_id
            built["session"] = setup.session
            built["regime"] = setup.regime
            built["signal_id"] = contract + "|" + setup.setup_id
            built["entry_definition"] = "first_bar_market_open_plus_slippage_not_limit_fill"
            built["candidate_entry"] = setup.entry
            built["stop_first"] = built.outcome.map(lambda x: None if x in {"AMBIGUOUS", "CENSORED"} else x == "SL_FIRST")
            built["timeout"] = built.outcome.eq("TIMEOUT")
            built["event_order_resolution"] = "bar_interval; simultaneous barriers ambiguous"
            minutes = pd.Timedelta(config.interval).total_seconds() / 60
            built["minutes_to_target_upper"] = (built.bars_to_target + 1) * minutes
            built["minutes_to_stop_upper"] = (built.bars_to_stop + 1) * minutes
            if setup.features.get("atr", 0) > 0:
                built["target_distance_atr"] = abs(built.target_price - built.entry_price) / setup.features["atr"]
            for key, value in setup.features.items():
                built[f"feature_{key}"] = value
            frames.append(built)
    if not frames:
        return pd.DataFrame()
    result = pd.concat(frames, ignore_index=True)
    result["instrument_id"] = spec.instrument_id
    return result


def readiness(contract_bars: pd.DataFrame | None, spec: InstrumentSpec) -> dict:
    """Describe whether authentic contract data is present."""
    if contract_bars is None or contract_bars.empty:
        return {"status": "DATA_BLOCKED", "reason": "NO_CONTRACT_DATA",
                "requires": "licensed raw-contract 1m/5m OHLCV with contract_id",
                "instrument": spec.instrument_id}
    try:
        quality = validate_contract_bars(contract_bars, spec)
    except ValueError as exc:
        return {"status": "DATA_BLOCKED", "reason": str(exc), "instrument": spec.instrument_id}
    return {"status": "STRUCTURALLY_VALID_PROVENANCE_REQUIRED", "instrument": spec.instrument_id, **quality}
