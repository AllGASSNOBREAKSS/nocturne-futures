import pandas as pd
from nocturne.research.target_diagnostics import nested_target_audit


def test_monotonicity_detects_invalid_nested_outcomes_but_not_different_stops():
    frame = pd.DataFrame([dict(signal_id="s", entry_price=100, stop_price=90, side="LONG", horizon_bars=24,
                              slippage_ticks_per_side=1, target_price=target, target_first=outcome,
                              target_touched=outcome) for target, outcome in ((110, False), (120, True))])
    assert len(nested_target_audit(frame)["violations"]) == 2
    frame.loc[1, "stop_price"] = 80
    assert nested_target_audit(frame)["comparisons"] == 0
