"""Replay checksum-linked raw-contract receipts using existing calculations.

Receipt verification is not proof of historical dissemination latency. No book,
trade profile, true VWAP or aggressive-volume feature is invented from bars.
"""
import json
import math
from dataclasses import replace
from pathlib import Path

import pandas as pd

from ..adapters.databento import normalize_csv, aggregate_five_minutes
from ..adapters.snapshots import canonical, digest
from ..auction.session import vwap
from ..sessions import session_window_for, _atr
from .contract_targets import ContractTargetConfig, build_contract_targets, validate_contract_bars


def load_contract_receipts(root, spec, contract):
    root = Path(root)
    frames, receipts = [], []
    for path in sorted(root.glob("*.json")):
        record = json.loads(path.read_text())
        request = record.get("request", {})
        if record.get("instrument") != spec.instrument_id or request.get("symbols") != contract:
            continue
        if (request.get("dataset") != "GLBX.MDP3" or request.get("stype_in") != "raw_symbol"
                or request.get("schema") != "ohlcv-1m" or not record.get("license_scope")):
            raise ValueError("contract receipt identity/license/schema mismatch")
        for filename, checksum in (("raw_file", "raw_sha256"), ("export_file", "export_sha256")):
            if Path(record[filename]).name != record[filename]:
                raise ValueError("invalid receipt filename")
            if digest((root / record[filename]).read_bytes()) != record[checksum]:
                raise ValueError("contract receipt checksum mismatch")
        raw = (root / record["raw_file"]).read_bytes()
        reconstructed = normalize_csv(raw, contract, pd.Timestamp(request["start"]), pd.Timestamp(request["end"]))
        exported = pd.read_csv(root / record["export_file"])
        for field in ("timestamp", "available_at"):
            exported[field] = pd.to_datetime(exported[field], utc=True)
        if not reconstructed.to_csv(index=False, lineterminator="\n") == exported[reconstructed.columns].to_csv(index=False, lineterminator="\n"):
            raise ValueError("raw/exported contract observations differ")
        validate_contract_bars(exported, spec, ContractTargetConfig(interval="1min", min_rows=1))
        receipt_id = digest(canonical(record))
        exported["source_receipt_id"] = receipt_id
        frames.append(exported)
        receipts.append({"receipt_id": receipt_id, "raw_sha256": record["raw_sha256"],
                         "export_sha256": record["export_sha256"], "received_at": record["received_at"],
                         "availability": record.get("availability", "UNVERIFIED")})
    if not frames:
        return {"status": "DATA_BLOCKED", "reason": "NO_VERIFIED_CONTRACT_RECEIPTS", "bars": pd.DataFrame(), "receipts": []}
    bars = pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    if bars.duplicated(["contract_id", "timestamp"]).any():
        raise ValueError("overlapping contract receipts require explicit reconciliation")
    return {"status": "SOURCE_RECEIPT_VERIFIED_RESEARCH_ONLY", "bars": bars, "receipts": receipts,
            "inventory_sha256": digest(canonical(receipts)),
            "pit_status": "BAR_END_LOWER_BOUND_NOT_VERIFIED_DISSEMINATION_OR_VINTAGE_HISTORY",
            "trading_decision": "NO_TRADE"}


def asof_contract_context(history, spec, contract, day, session, asof):
    asof = pd.Timestamp(asof)
    if asof.tzinfo is None:
        raise ValueError("timezone-aware asof required")
    if history["status"] == "DATA_BLOCKED":
        return {"status": "DATA_BLOCKED", "reason": history["reason"], "trading_decision": "NO_TRADE"}
    bars = history["bars"]
    window = session_window_for(spec, session, day)
    known = bars[(bars.contract_id == contract) & (bars.available_at <= asof)
                 & (bars.timestamp >= window.start_utc) & (bars.timestamp < window.end_utc)]
    if known.empty:
        return {"status": "DATA_BLOCKED", "reason": "NO_COMPLETED_SESSION_BARS_ASOF", "trading_decision": "NO_TRADE"}
    expected = pd.date_range(window.start_utc, min(asof, window.end_utc), freq="1min", inclusive="left")
    expected = expected[expected + pd.Timedelta("1min") <= asof]
    gaps = len(expected.difference(pd.DatetimeIndex(known.timestamp)))
    return {"status": "RESEARCH_STATE_ONLY", "contract_id": contract, "session": session,
            "asof": asof.isoformat(), "bars_available": len(known), "missing_minute_bars": gaps,
            "high": float(known.high.max()), "low": float(known.low.min()), "last_close": float(known.close.iloc[-1]),
            "bar_vwap_proxy": vwap(known) if known.volume.sum() > 0 else None,
            "vwap_definition": "typical-price bar proxy; not trade-derived VWAP",
            "poc": None, "vah": None, "val": None, "hvn": None, "lvn": None,
            "true_vwap": None, "cvd": None, "book_imbalance": None,
            "blocked_features": ["NO_AUTHENTIC_TRADE_RECEIPTS", "NO_QUOTE_RECEIPTS", "NO_DEPTH_RECEIPTS"],
            "feature_available_at": known.available_at.max().isoformat(),
            "source_receipt_ids": sorted(known.source_receipt_id.unique().tolist()),
            "pit_status": history["pit_status"], "calendar_status": "EXISTING_ENGINEERING_BASELINE_NOT_PROVIDER_AUTHORITATIVE",
            "direction_probability": None, "target_first_probability": None, "trading_decision": "NO_TRADE"}


def target_distance_study(history, spec, setups, horizons=(12, 24, 72), distances=(50., 100., 200., 350., 500.)):
    if history["status"] == "DATA_BLOCKED":
        return pd.DataFrame()
    if spec.instrument_id != "NQ":
        raise ValueError("this point-distance grid is NQ-specific; define a separate ES protocol")
    bars = aggregate_five_minutes(history["bars"])
    if bars.empty:
        return pd.DataFrame()
    results = []
    for horizon in horizons:
        for setup in setups:
            side = 1 if setup.side == "LONG" else -1
            # No unsupported externally supplied feature is silently accepted as PIT.
            known = bars[(bars.contract_id == setup.contract_id) & (bars.available_at <= pd.Timestamp(setup.asof))]
            atr = _atr(known) if not known.empty else float("nan")
            derived = {"atr": atr} if math.isfinite(atr) and atr > 0 else {}
            candidate = replace(setup, targets=tuple(setup.entry + side * d for d in distances), features=derived)
            built = build_contract_targets(bars, spec, [candidate], ContractTargetConfig(horizon_bars=horizon, min_rows=1))
            if built.empty:
                continue
            built["source_inventory_sha256"] = history["inventory_sha256"]
            built["pit_status"] = history["pit_status"]
            built["requested_distance_points"] = built.target_price.sub(candidate.entry).abs()
            built["target_grid_definition"] = "distance_from_candidate_entry; realized_fill_distance_recorded_separately"
            built["setup_context_status"] = "USER_SUPPLIED_STRATEGY_TAGS_NOT_PIT_CERTIFIED"
            built["derived_atr_available_at"] = known.available_at.max() if derived else None
            built["fill_target_distance_points"] = built.target_price.sub(built.entry_price).abs()
            built["target_first_probability"] = None
            built["promotion_status"] = "NO_PROMOTION"
            results.append(built)
    return pd.concat(results, ignore_index=True) if results else pd.DataFrame()
