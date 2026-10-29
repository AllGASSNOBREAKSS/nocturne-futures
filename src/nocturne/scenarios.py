"""Scenario math: expected close, directional odds, bucket lookup."""

from __future__ import annotations

from .models import Scenario


def midpoint(scenario: Scenario, code: str) -> float:
    low, high = scenario.closes[code]
    return (low + high) / 2.0


def expected_close(scenarios: tuple[Scenario, ...] | list[Scenario], code: str) -> float:
    return sum(s.probability * midpoint(s, code) for s in scenarios)


def down_probability(
    scenarios: tuple[Scenario, ...] | list[Scenario], code: str, prior_close: float
) -> float:
    return sum(s.probability for s in scenarios if midpoint(s, code) < prior_close)


def bucket_for(
    scenarios: tuple[Scenario, ...] | list[Scenario], code: str, price: float
) -> Scenario | None:
    for scenario in scenarios:
        low, high = scenario.closes[code]
        if low <= price <= high:
            return scenario
    return None


def probability_mass(scenarios: tuple[Scenario, ...] | list[Scenario]) -> float:
    return sum(s.probability for s in scenarios)
