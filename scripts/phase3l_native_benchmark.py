"""Benchmark the existing kernel on synthetic inputs, not market observations."""
import json
import platform
import statistics
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter

import numpy as np

from nocturne.auction.volume_profile import _bin_index

ROOT = Path(__file__).resolve().parents[1]


def main():
    try:
        import nocturne_native
    except ImportError:
        print(json.dumps({"status": "TOOLCHAIN_BLOCKED"}))
        return 1
    rng = np.random.default_rng(7)
    prices = (20000 + rng.integers(-400, 401, size=100000) * .25).tolist()
    quantities = rng.integers(1, 11, size=len(prices)).astype(float).tolist()
    def reference():
        bins = {}
        for price, quantity in zip(prices, quantities):
            bucket = _bin_index(price, .25, 1)
            bins[bucket] = bins.get(bucket, 0.) + quantity
        return bins
    def measure(function):
        durations = []
        for _ in range(5):
            start = perf_counter()
            output = function()
            durations.append(perf_counter() - start)
        return output, statistics.median(durations)
    expected, python_time = measure(reference)
    actual, native_time = measure(lambda: nocturne_native.sum_by_bin(prices, quantities, .25, 1))
    if expected != actual:
        raise ValueError("native aggregation parity failed")
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "status": "PARITY_VERIFIED",
              "input_origin": "SYNTHETIC_PERFORMANCE_FIXTURE_NOT_MARKET_DATA", "rows": len(prices), "repeats": 5,
              "python_seconds_median": python_time, "native_seconds_median_including_binding_conversion": native_time,
              "measured_speed_ratio": python_time / native_time, "python": platform.python_version(),
              "platform": platform.system(), "kernel": "existing sum_by_bin; no native rewrite",
              "warning": "host-specific microbenchmark, not end-to-end replay speed or predictive evidence"}
    (ROOT / "reports/phase3l_native_benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
