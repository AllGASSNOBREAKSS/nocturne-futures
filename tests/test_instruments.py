from datetime import date, datetime, timezone

import pytest

from nocturne.instruments import get_instrument, instrument_for_yahoo_symbol, list_instruments


def test_registry_contains_required_contracts():
    ids = {spec.instrument_id for spec in list_instruments()}
    assert {"NQ", "MNQ", "ES", "MES", "VX", "ZN", "ZB"} <= ids


def test_tick_values_are_consistent():
    nq = get_instrument("NQ")
    assert nq.tick_size == 0.25
    assert nq.multiplier == 20
    assert nq.tick_value == pytest.approx(5.0)
    assert nq.price_to_ticks(28_210.50) == 112_842
    assert nq.ticks_to_price(112_842) == pytest.approx(28_210.50)


def test_vx_is_cfe_not_cme():
    vx = get_instrument("VX")
    assert vx.venue == "CFE"
    assert vx.exchange == "Cboe Futures Exchange"


def test_treasury_tick_sizes():
    assert get_instrument("ZN").tick_size == pytest.approx(1 / 64)
    assert get_instrument("ZB").tick_size == pytest.approx(1 / 32)


def test_unknown_instrument_raises():
    with pytest.raises(KeyError):
        get_instrument("CL")


def test_yahoo_symbol_mapping():
    assert instrument_for_yahoo_symbol("NQ=F").instrument_id == "NQ"
    assert instrument_for_yahoo_symbol("VX=F") is None
