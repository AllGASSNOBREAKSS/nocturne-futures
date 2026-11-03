"""Nested-target checks for equivalent signal/entry/stop/horizon scenarios."""
import pandas as pd


def nested_target_audit(frame):
    keys = ["signal_id", "entry_price", "stop_price", "side", "horizon_bars", "slippage_ticks_per_side"]
    checked, violations = 0, []
    for key, group in frame.groupby(keys, dropna=False):
        group = group.assign(distance=(group.target_price - group.entry_price).abs()).sort_values("distance")
        for event in ("target_touched", "target_first"):
            known = group[group[event].notna()]
            for (_, near), (_, far) in zip(known.iloc[:-1].iterrows(), known.iloc[1:].iterrows()):
                checked += 1
                if float(near[event]) < float(far[event]):
                    violations.append({"signal_id": key[0], "event": event,
                                       "near": float(near.distance), "far": float(far.distance)})
    return {"comparisons": checked, "violations": violations,
            "unknowns": "censored/ambiguous outcomes excluded; no imputation"}


def target_timing(frame):
    result = {}
    for target, group in frame.groupby("target_id"):
        touched = group[group.target_touched == True]
        times = pd.to_numeric(touched.bars_to_target, errors="coerce").dropna() + 1
        result[target] = {"rows": len(group), "observed_touches": len(times),
                          "median_bars_to_touch_upper_bound": float(times.median()) if len(times) else None,
                          "p90_bars_to_touch_upper_bound": float(times.quantile(.9)) if len(times) else None,
                          "interpretation": "conditional_on_observed_touch; not a survival estimate"}
    return result
