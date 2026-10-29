import pytest

from nocturne.levels import distance, nearest_level, round_number_levels


def test_round_number_levels_bracket_the_price():
    below, above = round_number_levels(7763.5, 50)
    assert below == 7750
    assert above == 7800


def test_round_number_levels_skip_the_price_itself():
    below, above = round_number_levels(7800.0, 50)
    assert below == 7750
    assert above == 7850


def test_nearest_level_returns_signed_distance():
    name, value, diff = nearest_level(7763.5, {"r1": 7773.0, "s1": 7712.0})
    assert name == "r1"
    assert value == 7773.0
    assert diff == pytest.approx(-9.5)


def test_distance_is_positive_above_the_level():
    assert distance(7800.0, 7773.0) == pytest.approx(27.0)
    assert distance(7700.0, 7773.0) == pytest.approx(-73.0)
