#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

#include "aggregate.hpp"

PYBIND11_MODULE(nocturne_native, m) {
    m.doc() = "Nocturne native kernels (optional, parity-tested)";
    m.def(
        "sum_by_bin",
        &sum_by_bin,
        "Aggregate executed quantity by price bin",
        pybind11::arg("prices"),
        pybind11::arg("quantities"),
        pybind11::arg("tick_size"),
        pybind11::arg("bin_ticks") = 1
    );
}
