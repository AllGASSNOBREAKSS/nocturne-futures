#include "aggregate.hpp"

#include <cmath>
#include <stdexcept>

std::unordered_map<int, double> sum_by_bin(
    const std::vector<double>& prices,
    const std::vector<double>& quantities,
    double tick_size,
    int bin_ticks
) {
    if (tick_size <= 0.0 || bin_ticks <= 0) {
        throw std::invalid_argument("tick_size and bin_ticks must be positive");
    }
    if (prices.size() != quantities.size()) {
        throw std::invalid_argument("prices and quantities must have equal length");
    }

    std::unordered_map<int, double> bins;
    bins.reserve(prices.size());
    for (std::size_t i = 0; i < prices.size(); ++i) {
        const int tick = static_cast<int>(std::floor(prices[i] / tick_size + 1e-9));
        const int bin = tick / bin_ticks;
        bins[bin] += quantities[i];
    }
    return bins;
}
