import pandas as pd
from nocturne.adapters.contract_quality import contract_coverage, compare_sources


def test_contract_coverage_and_discrepancies_do_not_stitch_rolls():
    stamps = pd.date_range("2025-01-02T14:30Z", periods=3, freq="1min")
    left = pd.DataFrame(dict(timestamp=stamps[:2], contract_id="NQH5", close=100., volume=10))
    result = contract_coverage(left, {"NQH5": stamps, "NQM5": stamps})
    assert result["contracts"]["NQH5"]["missing"] == 1
    assert result["contracts"]["NQM5"]["missing"] == 3
    right = left.copy()
    right.loc[0, "close"] += .5
    assert compare_sources(left, right, .25)["close_disagreements"] == 1
    right["contract_id"] = "NQM5"
    assert compare_sources(left, right, .25)["matched"] == 0
