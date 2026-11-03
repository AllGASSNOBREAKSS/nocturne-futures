"""Contract-preserving bar validation using explicit expected exchange grids.

Callers supply holiday/session calendars and roll metadata. No generic weekday
rule can prove that CME/CFE market history is complete.
"""
import pandas as pd


def contract_coverage(frame, expected_by_contract):
    frame = frame.copy()
    frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
    if "contract_id" not in frame or frame.contract_id.isna().any():
        raise ValueError("contract IDs required; continuous proxies are ineligible")
    result = {}
    for contract, expected in expected_by_contract.items():
        expected = pd.DatetimeIndex(pd.to_datetime(expected, utc=True))
        sample = frame[frame.contract_id == contract]
        actual = pd.DatetimeIndex(sample.timestamp)
        result[contract] = {"rows": len(sample), "expected": len(expected),
                            "missing": len(expected.difference(actual)),
                            "outside_grid": len(actual.difference(expected)),
                            "duplicate_timestamps": int(actual.duplicated().sum())}
    return {"contracts": result, "unexpected_contracts": sorted(set(frame.contract_id) - set(expected_by_contract)),
            "roll_adjustment": "none; raw contracts kept separate"}


def compare_sources(left, right, tolerance):
    keys = ["contract_id", "timestamp"]
    if tolerance < 0:
        raise ValueError("nonnegative tolerance required")
    left, right = left.copy(), right.copy()
    for frame in (left, right):
        frame["timestamp"] = pd.to_datetime(frame.timestamp, utc=True)
        if frame.duplicated(keys).any():
            raise ValueError("duplicate source records")
    merged = left.merge(right, on=keys, suffixes=("_left", "_right"), how="outer", indicator=True)
    matched = merged[merged._merge == "both"]
    return {"matched": len(matched), "left_only": int((merged._merge == "left_only").sum()),
            "right_only": int((merged._merge == "right_only").sum()),
            "close_disagreements": int(((matched.close_left - matched.close_right).abs() > tolerance).sum()),
            "volume_disagreements": int((matched.volume_left != matched.volume_right).sum())}
