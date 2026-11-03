#pragma once

#include <unordered_map>
#include <vector>

// Bin executed quantity by price. The Python reference is authoritative.
std::unordered_map<int, double> sum_by_bin(
    const std::vector<double>& prices,
    const std::vector<double>& quantities,
    double tick_size,
    int bin_ticks
);
