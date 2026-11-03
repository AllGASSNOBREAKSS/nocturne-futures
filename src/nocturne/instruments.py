"""Instrument registry with venue, tick, multiplier and roll metadata.

Values are the standard CME/CBOT/CFE contract specifications. Production use
must reconcile them with provider-authoritative contract files; the registry is
the single place to change them.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date
from typing import Iterable


@dataclass(frozen=True)
class InstrumentSpec:
    instrument_id: str
    root_symbol: str
    name: str
    venue: str
    exchange: str
    currency: str
    tick_size: float
    tick_value: float
    multiplier: float
    session_calendar: str
    timezone: str
    volume_units: str
    feed_entitlement: str
    adjustment_policy: str
    active_roll_rule: str
    contract_months: tuple[int, ...]
    yahoo_symbol: str | None = None

    def price_to_ticks(self, price: float) -> int:
        return int(round(price / self.tick_size))

    def ticks_to_price(self, ticks: int) -> float:
        return round(ticks * self.tick_size, 10)

    def with_contract(self, contract_id: str | None, expiry: date | None = None) -> "InstrumentSpec":
        return replace(self, instrument_id=self.instrument_id) if contract_id is None else self


_REGISTRY: dict[str, InstrumentSpec] = {
    "NQ": InstrumentSpec(
        instrument_id="NQ",
        root_symbol="NQ",
        name="E-mini Nasdaq-100",
        venue="CME",
        exchange="CME",
        currency="USD",
        tick_size=0.25,
        tick_value=5.00,
        multiplier=20.0,
        session_calendar="CME_EQUITY_INDEX",
        timezone="America/New_York",
        volume_units="contracts",
        feed_entitlement="CME_MDP3_REQUIRED",
        adjustment_policy="RAW_FRONT_MONTH",
        active_roll_rule="VOLUME_OI_CROSSOVER_5D_BEFORE_EXPIRY",
        contract_months=(3, 6, 9, 12),
        yahoo_symbol="NQ=F",
    ),
    "MNQ": InstrumentSpec(
        instrument_id="MNQ",
        root_symbol="MNQ",
        name="Micro E-mini Nasdaq-100",
        venue="CME",
        exchange="CME",
        currency="USD",
        tick_size=0.25,
        tick_value=0.50,
        multiplier=2.0,
        session_calendar="CME_EQUITY_INDEX",
        timezone="America/New_York",
        volume_units="contracts",
        feed_entitlement="CME_MDP3_REQUIRED",
        adjustment_policy="RAW_FRONT_MONTH",
        active_roll_rule="VOLUME_OI_CROSSOVER_5D_BEFORE_EXPIRY",
        contract_months=(3, 6, 9, 12),
        yahoo_symbol=None,
    ),
    "ES": InstrumentSpec(
        instrument_id="ES",
        root_symbol="ES",
        name="E-mini S&P 500",
        venue="CME",
        exchange="CME",
        currency="USD",
        tick_size=0.25,
        tick_value=12.50,
        multiplier=50.0,
        session_calendar="CME_EQUITY_INDEX",
        timezone="America/New_York",
        volume_units="contracts",
        feed_entitlement="CME_MDP3_REQUIRED",
        adjustment_policy="RAW_FRONT_MONTH",
        active_roll_rule="VOLUME_OI_CROSSOVER_5D_BEFORE_EXPIRY",
        contract_months=(3, 6, 9, 12),
        yahoo_symbol="ES=F",
    ),
    "MES": InstrumentSpec(
        instrument_id="MES",
        root_symbol="MES",
        name="Micro E-mini S&P 500",
        venue="CME",
        exchange="CME",
        currency="USD",
        tick_size=0.25,
        tick_value=1.25,
        multiplier=5.0,
        session_calendar="CME_EQUITY_INDEX",
        timezone="America/New_York",
        volume_units="contracts",
        feed_entitlement="CME_MDP3_REQUIRED",
        adjustment_policy="RAW_FRONT_MONTH",
        active_roll_rule="VOLUME_OI_CROSSOVER_5D_BEFORE_EXPIRY",
        contract_months=(3, 6, 9, 12),
        yahoo_symbol=None,
    ),
    "VX": InstrumentSpec(
        instrument_id="VX",
        root_symbol="VX",
        name="Cboe VIX Futures",
        venue="CFE",
        exchange="Cboe Futures Exchange",
        currency="USD",
        tick_size=0.01,
        tick_value=10.00,
        multiplier=1000.0,
        session_calendar="CFE_VX",
        timezone="America/New_York",
        volume_units="contracts",
        feed_entitlement="CFE_MARKET_DATA_REQUIRED",
        adjustment_policy="RAW_FRONT_MONTH",
        active_roll_rule="MONTHLY_CASH_SETTLEMENT",
        contract_months=(1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12),
        yahoo_symbol=None,
    ),
    "ZN": InstrumentSpec(
        instrument_id="ZN",
        root_symbol="ZN",
        name="10-Year T-Note Futures",
        venue="CBOT",
        exchange="CBOT",
        currency="USD",
        tick_size=1.0 / 64.0,
        tick_value=15.625,
        multiplier=1000.0,
        session_calendar="CBOT_TREASURY",
        timezone="America/New_York",
        volume_units="contracts",
        feed_entitlement="CME_MDP3_REQUIRED",
        adjustment_policy="RAW_FRONT_MONTH",
        active_roll_rule="QUARTERLY_VOLUME_OI",
        contract_months=(3, 6, 9, 12),
        yahoo_symbol="ZN=F",
    ),
    "ZB": InstrumentSpec(
        instrument_id="ZB",
        root_symbol="ZB",
        name="30-Year T-Bond Futures",
        venue="CBOT",
        exchange="CBOT",
        currency="USD",
        tick_size=1.0 / 32.0,
        tick_value=31.25,
        multiplier=1000.0,
        session_calendar="CBOT_TREASURY",
        timezone="America/New_York",
        volume_units="contracts",
        feed_entitlement="CME_MDP3_REQUIRED",
        adjustment_policy="RAW_FRONT_MONTH",
        active_roll_rule="QUARTERLY_VOLUME_OI",
        contract_months=(3, 6, 9, 12),
        yahoo_symbol="ZB=F",
    ),
}


def get_instrument(instrument_id: str) -> InstrumentSpec:
    try:
        return _REGISTRY[instrument_id.upper()]
    except KeyError as exc:
        raise KeyError(f"unknown instrument {instrument_id!r}") from exc


def list_instruments() -> Iterable[InstrumentSpec]:
    return tuple(_REGISTRY.values())


def instrument_for_yahoo_symbol(symbol: str) -> InstrumentSpec | None:
    for spec in _REGISTRY.values():
        if spec.yahoo_symbol == symbol:
            return spec
    return None
