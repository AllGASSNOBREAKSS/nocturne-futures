# Native Kernels — Built Locally, Parity Passed

**Status:** built locally with MSVC 19.51 (`Visual Studio 18`) and pybind11 3.1;
the parity test passes. CI also builds the module on Ubuntu. The Python
reference remains the source of truth.

## Verified build

```text
CMake 4.x + Ninja + MSVC 19.51
nocturne_native.cp314-win_amd64.pyd
tests/test_native_parity.py  ->  passed
```

With the module on `PYTHONPATH`, the full suite is **122 passed**. Without it,
the parity test is skipped and the suite is **121 passed, 1 skipped**.

## Intended use

Only profiled hotspots:

1. tick/volume aggregation by price bin,
2. rolling volume-profile updates,
3. deterministic book replay.

## Build contract

```bash
python -m pip install pybind11 cmake ninja
cmake -S native -B native/build -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -Dpybind11_DIR=$(python -m pybind11 --cmakedir)
cmake --build native/build
PYTHONPATH=native/build python -m pytest tests/test_native_parity.py -q
```

The module name is `nocturne_native`. The first function is:

```python
nocturne_native.sum_by_bin(prices, quantities, tick_size, bin_ticks) -> dict[int, float]
```

Parity fixture:

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
