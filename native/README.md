# Native Kernels — TOOLCHAIN_BLOCKED

**Status: not built.** This environment has no `cmake`, `g++`, MSVC C++ workload,
or `pybind11`. No native artifact is installed and no parity claim is made.

## Intended use

Only profiled hotspots:

1. tick/volume aggregation by price bin,
2. rolling volume-profile updates,
3. deterministic book replay.

The Python reference in `src/nocturne/auction/volume_profile.py` and
`src/nocturne/orderflow/depth.py` remains the source of truth.

## Build contract

```bash
python -m pip install pybind11
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build --config Release
```

The module name is `nocturne_native`. The first function is:

```python
nocturne_native.sum_by_bin(prices, quantities, tick_size, bin_ticks) -> dict[int, float]
```

It must match the Python reference on the same fixture:

```python
prices = [100.0, 100.2, 101.0]
quantities = [1.0, 2.0, 3.0]
tick_size = 0.25
bin_ticks = 1
# expected: {400: 3.0, 404: 3.0}
```

## Promotion rule

The native path is optional. It is used only if:

- the Python profile is correct and tested,
- a benchmark shows the Python path is the bottleneck,
- the native output matches Python on golden fixtures,
- sanitizer/debug/release builds pass,
- the Python fallback stays available.

No C++ code has access to broker credentials or order permissions.
