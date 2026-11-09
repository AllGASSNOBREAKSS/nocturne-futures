# Phase 4C — signal intelligence (authentic NQ/ES, 2010–2026)

69 candidates, 0 accepted.

## Did any strategy capture large NQ days?

| Strategy | Day range | Sessions | Trades | Win % | Mean pts | Share of range | Best pts |
|---|---|---|---|---|---|---|---|
| NQ_opening_range_breakout | >=100 | 2111 | 1979 | 54.1 | 3.65 | -0.7% | 740.75 |
| NQ_opening_range_breakout | >=200 | 1404 | 1331 | 56.8 | 7.98 | 0.6% | 740.75 |
| NQ_opening_range_breakout | >=350 | 631 | 604 | 63.1 | 22.96 | 3.6% | 740.75 |
| NQ_opening_range_breakout | >=500 | 283 | 272 | 65.1 | 35.62 | 4.2% | 740.75 |
| NQ_value_rejection | >=100 | 2111 | 1360 | 45.3 | -0.97 | -0.2% | 241.75 |
| NQ_value_rejection | >=200 | 1404 | 886 | 44.1 | -1.81 | -0.5% | 241.75 |
| NQ_value_rejection | >=350 | 631 | 372 | 43.8 | -1.93 | -0.4% | 241.75 |
| NQ_value_rejection | >=500 | 283 | 164 | 48.8 | 3.11 | 1.0% | 241.75 |
| NQ_vwap_pullback | >=100 | 2111 | 1764 | 50.2 | -1.12 | -0.6% | 198.34 |
| NQ_vwap_pullback | >=200 | 1404 | 1158 | 50.3 | -0.38 | -0.0% | 198.34 |
| NQ_vwap_pullback | >=350 | 631 | 490 | 50.0 | -0.53 | 0.2% | 198.34 |
| NQ_vwap_pullback | >=500 | 283 | 213 | 46.0 | -6.04 | -0.7% | 198.34 |
| studio: QA trend continuation NQ | >=100 | 2111 | 665 | 48.3 | -1.85 | -1.5% | 265.92 |
| studio: QA trend continuation NQ | >=200 | 1404 | 468 | 50.0 | -0.33 | -0.5% | 265.92 |
| studio: QA trend continuation NQ | >=350 | 631 | 192 | 51.0 | 7.36 | 1.6% | 265.92 |
| studio: QA trend continuation NQ | >=500 | 283 | 84 | 51.2 | 4.44 | 0.5% | 265.92 |
| studio: QA VWAP pullback NQ 16y | >=100 | 2111 | 1764 | 50.2 | -1.12 | -0.6% | 198.34 |
| studio: QA VWAP pullback NQ 16y | >=200 | 1404 | 1158 | 50.3 | -0.38 | -0.0% | 198.34 |
| studio: QA VWAP pullback NQ 16y | >=350 | 631 | 490 | 50.0 | -0.53 | 0.2% | 198.34 |
| studio: QA VWAP pullback NQ 16y | >=500 | 283 | 213 | 46.0 | -6.04 | -0.7% | 198.34 |

## Evidence ranking (top 25)

| # | Signal | Origin | Dev n | Dev EV [CI] | Hold n | Hold EV [CI] | Status |
|---|---|---|---|---|---|---|---|
| 1 | ML-filtered NQ long 0.25x0.25 ATR (lightgbm) | phase4c_ml | 87 | -0.027 [-0.227, 0.172] | 3 | 0.993 [0.990, 0.995] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 2 | ML-filtered NQ short 0.25x0.25 ATR (lightgbm) | phase4c_ml | 49 | 0.099 [-0.178, 0.376] | 161 | 0.108 [-0.042, 0.259] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 3 | ML-filtered ES long 0.25x0.25 ATR (lightgbm) | phase4c_ml | 121 | -0.013 [-0.188, 0.162] | 180 | -0.005 [-0.145, 0.134] | REJECTED (DEVELOPMENT_EV_CI_NOT_POSITIVE) |
| 4 | ML-filtered NQ short 0.25x0.25 ATR (logistic) | phase4c_ml | 151 | 0.032 [-0.126, 0.190] | 237 | -0.050 [-0.174, 0.074] | REJECTED (DEVELOPMENT_EV_CI_NOT_POSITIVE) |
| 5 | ML-filtered NQ long 0.5x0.5 ATR (lightgbm) | phase4c_ml | 9 | -0.346 [-0.999, 0.307] | 10 | 0.396 [-0.202, 0.995] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 6 | ML-filtered ES short 0.25x0.25 ATR (logistic) | phase4c_ml | 375 | -0.130 [-0.230, -0.030] | 224 | -0.089 [-0.217, 0.040] | REJECTED (DEVELOPMENT_EV_CI_NOT_POSITIVE) |
| 7 | ML-filtered ES long 0.5x0.5 ATR (logistic) | phase4c_ml | 42 | 0.004 [-0.282, 0.289] | 32 | 0.050 [-0.269, 0.369] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 8 | ML-filtered ES short 0.25x0.25 ATR (lightgbm) | phase4c_ml | 200 | -0.069 [-0.205, 0.066] | 172 | -0.140 [-0.287, 0.007] | REJECTED (DEVELOPMENT_EV_CI_NOT_POSITIVE) |
| 9 | ML-filtered ES long 0.25x0.25 ATR (logistic) | phase4c_ml | 119 | -0.091 [-0.266, 0.085] | 61 | -0.049 [-0.298, 0.199] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 10 | ML-filtered NQ short 0.5x0.25 ATR (lightgbm) | phase4c_ml | 53 | -0.125 [-0.491, 0.241] | 91 | -0.067 [-0.329, 0.195] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 11 | ML-filtered ES short 0.5x0.25 ATR (logistic) | phase4c_ml | 84 | -0.101 [-0.404, 0.202] | 115 | -0.084 [-0.330, 0.161] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 12 | ML-filtered NQ long 0.5x0.5 ATR (logistic) | phase4c_ml | 40 | -0.138 [-0.423, 0.147] | 25 | 0.048 [-0.333, 0.428] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 13 | ML-filtered ES short 0.5x0.25 ATR (lightgbm) | phase4c_ml | 55 | -0.201 [-0.542, 0.141] | 171 | -0.222 [-0.410, -0.034] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 14 | ML-filtered ES long 1.0x0.5 ATR (logistic) | phase4c_ml | 12 | -0.299 [-0.900, 0.301] | 8 | 0.623 [-0.413, 1.658] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 15 | ML-filtered ES short 0.5x0.5 ATR (lightgbm) | phase4c_ml | 8 | 0.104 [-0.448, 0.656] | 27 | -0.147 [-0.482, 0.188] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 16 | ML-filtered NQ short 0.5x0.25 ATR (logistic) | phase4c_ml | 102 | 0.117 [-0.160, 0.394] | 57 | -0.226 [-0.552, 0.100] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 17 | ML-filtered ES long 0.5x0.5 ATR (lightgbm) | phase4c_ml | 37 | 0.252 [-0.033, 0.536] | 8 | 0.127 [-0.558, 0.813] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 18 | ML-filtered NQ long 0.5x0.25 ATR (logistic) | phase4c_ml | 61 | -0.323 [-0.633, -0.014] | 32 | -0.276 [-0.713, 0.162] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 19 | ML-filtered NQ long 0.25x0.25 ATR (logistic) | phase4c_ml | 182 | -0.088 [-0.228, 0.053] | 17 | -0.366 [-0.809, 0.076] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 20 | ML-filtered ES short 1.0x0.5 ATR (lightgbm) | phase4c_ml | 4 | -0.501 [-1.256, 0.253] | 12 | -0.252 [-0.813, 0.308] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 21 | ML-filtered ES long 0.5x0.25 ATR (logistic) | phase4c_ml | 55 | -0.037 [-0.402, 0.328] | 24 | -0.328 [-0.834, 0.178] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 22 | ML-filtered NQ short 0.5x0.5 ATR (lightgbm) | phase4c_ml | 7 | -0.259 [-0.851, 0.332] | 12 | -0.394 [-0.881, 0.094] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 23 | ML-filtered NQ long 0.5x0.25 ATR (lightgbm) | phase4c_ml | 40 | -0.389 [-0.744, -0.034] | 8 | -0.039 [-0.951, 0.873] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 24 | ML-filtered ES long 1.0x0.5 ATR (lightgbm) | phase4c_ml | 17 | -0.386 [-0.914, 0.143] | 3 | 0.395 [-0.988, 1.779] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
| 25 | ML-filtered ES short 0.5x0.5 ATR (logistic) | phase4c_ml | 29 | -0.260 [-0.569, 0.049] | 9 | -0.357 [-1.011, 0.296] | REJECTED (INSUFFICIENT_INDEPENDENT_SAMPLE) |
