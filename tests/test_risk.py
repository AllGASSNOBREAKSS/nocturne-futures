from datetime import datetime, timedelta, timezone

from nocturne.contracts import Decision
from nocturne.risk import RiskConfig, RiskContext, evaluate_risk

UTC = timezone.utc
NOW = datetime(2026, 11, 3, 15, 0, tzinfo=UTC)


def context(**overrides):
    base = dict(now=NOW, watermark=NOW - timedelta(minutes=5), coverage=1.0, market_open=True)
    base.update(overrides)
    return RiskContext(**base)


def test_normal_context_allows_wait():
    decision = evaluate_risk(context())
    assert decision.allow_new_risk is True
    assert decision.decision == Decision.WAIT
    assert decision.reason_codes == []


def test_stale_data_blocks():
    decision = evaluate_risk(context(watermark=NOW - timedelta(days=2)))
    assert decision.allow_new_risk is False
    assert decision.decision == Decision.NO_TRADE
    assert "STALE_DATA" in decision.reason_codes


def test_low_coverage_blocks():
    decision = evaluate_risk(context(coverage=0.5))
    assert "LOW_COVERAGE" in decision.reason_codes


def test_event_lock_blocks():
    decision = evaluate_risk(context(minutes_to_event=10))
    assert "PRE_EVENT_LOCK" in decision.reason_codes


def test_extreme_volatility_blocks():
    decision = evaluate_risk(context(atr_percentile=0.99))
    assert "EXTREME_VOLATILITY" in decision.reason_codes


def test_expired_and_duplicate_block():
    decision = evaluate_risk(
        context(signal_expires_at=NOW - timedelta(minutes=1), duplicate=True)
    )
    assert "SIGNAL_EXPIRED" in decision.reason_codes
    assert "DUPLICATE_SIGNAL" in decision.reason_codes
