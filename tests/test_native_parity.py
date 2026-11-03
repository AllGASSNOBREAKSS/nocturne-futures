"""Parity contract for the optional native kernel.

Skipped when the native module is not built (TOOLCHAIN_BLOCKED). The Python
reference is authoritative; this test only proves parity when the module exists.
"""

import pytest

native = pytest.importorskip(
    "nocturne_native",
    reason="native module not built: cmake/g++/pybind11 unavailable",
)


def python_sum_by_bin(prices, quantities, tick_size, bin_ticks=1):
    bins = {}
    for price, qty in zip(prices, quantities):
        tick = int((price / tick_size) + 1e-9)
        bucket = tick // bin_ticks
        bins[bucket] = bins.get(bucket, 0.0) + qty
    return bins


def test_sum_by_bin_matches_python():
    prices = [100.0, 100.2, 101.0]
    quantities = [1.0, 2.0, 3.0]
    expected = python_sum_by_bin(prices, quantities, 0.25, 1)
    result = native.sum_by_bin(prices, quantities, 0.25, 1)
    assert result == expected
    assert expected == {400: 3.0, 404: 3.0}
