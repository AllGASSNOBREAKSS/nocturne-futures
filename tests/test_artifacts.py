import json
from pathlib import Path

import pytest

from nocturne.models import Call, Scenario
from nocturne.scenarios import bucket_for, down_probability, expected_close
from nocturne.score import score_call, summary

ROOT = Path(__file__).resolve().parents[1]
CALL_PATH = ROOT / "data" / "snapshots" / "2026-10-27" / "call.json"
ACTUAL_PATH = ROOT / "data" / "snapshots" / "2026-10-28" / "actual.json"


def load_call() -> Call:
    return Call.load(CALL_PATH)


def load_actual() -> dict:
    return json.loads(ACTUAL_PATH.read_text(encoding="utf-8"))


def test_call_artifact_is_complete():
    call = load_call()
    assert call.call_id == "2026-10-27"
    assert call.session == "2026-10-28"
    assert set(call.instruments) == {"ES", "NQ", "GC", "SI"}
    assert sum(s.probability for s in call.scenarios) == pytest.approx(1.0)


def test_scenario_math():
    scenarios = (
        Scenario("a", "A", 0.6, {"ES": (100.0, 110.0)}),
        Scenario("b", "B", 0.4, {"ES": (90.0, 100.0)}),
    )
    assert expected_close(scenarios, "ES") == pytest.approx(101.0)
    assert down_probability(scenarios, "ES", 105.0) == pytest.approx(0.4)
    assert bucket_for(scenarios, "ES", 95.0).name == "b"
    assert bucket_for(scenarios, "ES", 120.0) is None


def test_known_scorecard():
    call = load_call()
    actual = load_actual()
    rows = {row.code: row for row in score_call(call, actual)}
    stats = summary(list(rows.values()))

    # Gold was the clean hit.
    assert rows["GC"].direction_hit
    assert rows["GC"].band_hit
    assert rows["GC"].range_hit

    # ES and NQ were wrong on direction and missed the close band.
    assert not rows["ES"].direction_hit
    assert not rows["ES"].band_hit
    assert not rows["NQ"].direction_hit
    assert not rows["NQ"].band_hit

    # Silver called the direction and the range, but not the close band.
    assert rows["SI"].direction_hit
    assert rows["SI"].range_hit
    assert not rows["SI"].band_hit

    assert stats["direction"] == pytest.approx(0.5)
    assert stats["band"] == pytest.approx(0.25)
    assert stats["range_full"] == pytest.approx(0.5)
    assert stats["range_any"] == pytest.approx(1.0)


def test_sigma_close_is_published_not_recomputed():
    call = load_call()
    assert call.sigma_close["ES"] == (65.0, 85.0)
    assert call.sigma_close["SI"] == (0.95, 1.2)
