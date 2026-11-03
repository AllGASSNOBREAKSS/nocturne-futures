"""Canonical Pydantic contracts for the v2 backend.

These mirror the JSON Schemas in the architecture package:
  - market_event.schema.json
  - market_level.schema.json
  - prediction.schema.json

Internal research objects use dataclasses; anything crossing a boundary
(adapter -> store -> API -> journal) uses these models.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Quality(BaseModel):
    model_config = ConfigDict(extra="allow")

    stale: bool = False
    missing: bool = False
    out_of_order: bool = False
    coverage: float = Field(default=1.0, ge=0.0, le=1.0)


class Zone(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lower_price_ticks: int
    upper_price_ticks: int

    @model_validator(mode="after")
    def _ordered(self) -> "Zone":
        if self.lower_price_ticks > self.upper_price_ticks:
            raise ValueError("lower_price_ticks must be <= upper_price_ticks")
        return self


class EventType(str, Enum):
    TRADE = "trade"
    BAR = "bar"
    QUOTE = "quote"
    BOOK_SNAPSHOT = "book_snapshot"
    BOOK_DELTA = "book_delta"
    ECONOMIC_RELEASE = "economic_release"
    NEWS_HEADLINE = "news_headline"
    OPTIONS_SNAPSHOT = "options_snapshot"
    MARKET_STATUS = "market_status"


class MarketEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    contract_id: str | None = None
    venue: str | None = None
    event_type: EventType
    event_time_utc: datetime
    available_at_utc: datetime
    received_at_utc: datetime
    source_sequence: int | None = None
    source_revision: int = Field(default=0, ge=0)
    license_scope: str = "public"
    payload: dict[str, Any]
    quality: Quality = Field(default_factory=Quality)

    @model_validator(mode="after")
    def _time_order(self) -> "MarketEvent":
        if self.available_at_utc < self.event_time_utc:
            raise ValueError("available_at_utc must be >= event_time_utc")
        if self.received_at_utc < self.available_at_utc:
            raise ValueError("received_at_utc must be >= available_at_utc")
        return self


class LevelSource(str, Enum):
    POC = "POC"
    VAH = "VAH"
    VAL = "VAL"
    HVN = "HVN"
    LVN = "LVN"
    TPO_POC = "TPO_POC"
    TPO_VAH = "TPO_VAH"
    TPO_VAL = "TPO_VAL"
    IB_HIGH = "IB_HIGH"
    IB_LOW = "IB_LOW"
    VWAP = "VWAP"
    SESSION_HIGH = "SESSION_HIGH"
    SESSION_LOW = "SESSION_LOW"
    SWING = "SWING"
    VOLATILITY_PROJECTION = "VOLATILITY_PROJECTION"
    OTHER = "OTHER"


class SessionType(str, Enum):
    RTH = "RTH"
    ETH = "ETH"
    OVERNIGHT = "OVERNIGHT"
    COMPOSITE = "COMPOSITE"
    CUSTOM = "CUSTOM"


class MarketLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    contract_id: str | None = None
    source_type: LevelSource
    session_type: SessionType
    asof_utc: datetime
    valid_until_utc: datetime | None = None
    lower_price_ticks: int
    upper_price_ticks: int
    calculation_version: str = "v2.0"
    profile_window: str | None = None
    volume_profile_method: str | None = None
    data_requirements: list[str] = Field(default_factory=list)
    quality: Quality = Field(default_factory=Quality)

    @model_validator(mode="after")
    def _ordered(self) -> "MarketLevel":
        if self.lower_price_ticks > self.upper_price_ticks:
            raise ValueError("lower_price_ticks must be <= upper_price_ticks")
        return self


class Target(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_id: str = Field(min_length=1)
    zone: Zone
    event_definition: str = Field(min_length=1)
    p_target_before_stop_given_fill: float | None = Field(default=None, ge=0.0, le=1.0)
    p_timeout_given_fill: float | None = Field(default=None, ge=0.0, le=1.0)
    time_to_target_seconds_p50: float | None = Field(default=None, ge=0.0)


class Bias(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class Decision(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    WAIT = "WAIT"
    NO_TRADE = "NO_TRADE"


class ResearchStatus(str, Enum):
    ILLUSTRATIVE = "ILLUSTRATIVE"
    RESEARCH_ONLY = "RESEARCH_ONLY"
    VALIDATED_SHADOW = "VALIDATED_SHADOW"
    PAPER_TESTED = "PAPER_TESTED"
    LIVE_APPROVED = "LIVE_APPROVED"


class Prediction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prediction_id: str = Field(min_length=1)
    instrument_id: str = Field(min_length=1)
    contract_id: str | None = None
    asof_utc: datetime
    data_watermark_utc: datetime
    expires_at_utc: datetime | None = None
    horizon_seconds: int = Field(ge=1)
    bias: Bias
    decision: Decision
    market_regime: str = Field(min_length=1)
    critical_day_state: str = Field(min_length=1)
    strategy_id: str = Field(min_length=1)
    strategy_version: str | None = None
    model_version: str = Field(min_length=1)
    feature_snapshot_hash: str | None = None
    p_entry_fill: float | None = Field(default=None, ge=0.0, le=1.0)
    entry: Zone
    stop: Zone
    targets: list[Target] = Field(default_factory=list)
    expected_net_value_points: float | None = None
    data_quality: Quality = Field(default_factory=Quality)
    reason_codes: list[str] = Field(default_factory=list)
    research_status: ResearchStatus = ResearchStatus.RESEARCH_ONLY
    latency_ms: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def _decision_consistency(self) -> "Prediction":
        if self.decision in (Decision.LONG, Decision.SHORT) and not self.targets:
            raise ValueError("LONG/SHORT predictions require at least one target")
        if self.decision == Decision.NO_TRADE and self.expected_net_value_points not in (None, 0.0):
            raise ValueError("NO_TRADE predictions must not claim positive expected value")
        return self


class RiskDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Decision
    reason_codes: list[str]
    critical_day_state: str
    data_quality: Quality
    allow_new_risk: bool
