from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from nocturne.instruments import get_instrument
from nocturne.research.contract_targets import (ContractSetup, ContractTargetConfig,
                                                build_contract_targets, readiness,
                                                validate_contract_bars)

UTC = timezone.utc
NQ = get_instrument("NQ")
START = datetime(2026, 11, 2, 14, 30, tzinfo=UTC)


def bars(count=60, contract="NQZ6"):
    stamps = pd.date_range(START, periods=count, freq="5min")
    price = 20000.0 + pd.Series(range(count)) * 0.25
    return pd.DataFrame({
        "timestamp": stamps, "available_at": stamps + pd.Timedelta("5min"),
        "contract_id": contract,
        "open": price.to_numpy(), "high": (price + 1.0).to_numpy(),
        "low": (price - 1.0).to_numpy(), "close": price.to_numpy(), "volume": 100.0,
    })


def setup(contract="NQZ6", asof=None, targets=(20002.0, 20004.0)):
    return ContractSetup(setup_id="s1", contract_id=contract,
                         asof=(asof or START + timedelta(minutes=5)).isoformat(),
                         side="LONG", entry=20000.0, stop=19998.0, targets=targets,
                         session="NEW_YORK", regime="TREND_UP", features={"atr": 2.0})


def test_contract_validation_accepts_aligned_ticks_and_reports_quality():
    report = validate_contract_bars(bars(), NQ)
    assert report["contracts"] == ["NQZ6"]
    assert report["tick_aligned"] is True


def test_contract_validation_rejects_continuous_proxy_and_misaligned_ticks():
    frame = bars()
    frame["contract_id"] = None
    with pytest.raises(ValueError, match="contract_id required"):
        validate_contract_bars(frame, NQ)
    off_tick = bars()
    off_tick.loc[0, "open"] = 20000.1
    with pytest.raises(ValueError, match="tick size"):
        validate_contract_bars(off_tick, NQ)


def test_contract_validation_rejects_duplicates_and_bad_availability():
    frame = bars()
    duplicated = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="duplicate"):
        validate_contract_bars(duplicated, NQ)
    early = bars()
    early.loc[0, "available_at"] = early.loc[0, "timestamp"]
    with pytest.raises(ValueError, match="bar completion"):
        validate_contract_bars(early, NQ)


def test_targets_are_built_per_contract_with_metadata():
    result = build_contract_targets(bars(), NQ, [setup()],
                                    ContractTargetConfig(horizon_bars=6, slippage_ticks=1.0))
    assert len(result) == 2
    assert set(result.contract_id) == {"NQZ6"}
    assert set(result.setup_id) == {"s1"}
    assert set(result.session) == {"NEW_YORK"}
    assert "feature_atr" in result.columns
    assert result.target_first.notna().all()


def test_setup_for_a_different_contract_is_not_mixed():
    result = build_contract_targets(bars(), NQ, [setup(contract="NQM6")],
                                    ContractTargetConfig(horizon_bars=6))
    assert result.empty


def test_readiness_is_fail_closed_without_contract_data():
    blocked = readiness(None, NQ)
    assert blocked["status"] == "DATA_BLOCKED"
    assert "licensed" in blocked["requires"]
    assert readiness(bars(), NQ)["status"] == "STRUCTURALLY_VALID_PROVENANCE_REQUIRED"
