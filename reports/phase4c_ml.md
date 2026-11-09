# Phase 4C — ML research on authentic NQ/ES sessions (Databento 2010–2026)

Generated 2026-11-09T06:32:43.160193+00:00. 110 experiments run through the desktop job store. Test years 2012–2026, holdout 2023–2026 (reused). Brier Δ = model − trailing-frequency baseline (negative is better).

Verdicts: {'ACCEPT_RESEARCH_ONLY': 47, 'INCONCLUSIVE': 44, 'REJECT': 19}

## Classification objectives

| Root | Objective | Model | Dev n | Dev AUC | Dev Brier (base) | Dev Δ [95% CI] | Hold AUC | Hold Δ | Max cal. gap | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| NQ | direction | logistic | 1935 | 0.480 | 0.2525 (0.2472) | +0.0053 [+0.0024, +0.0083] | 0.491 | +0.0025 | 0.124 | REJECT |
| NQ | direction | lightgbm | 1935 | 0.471 | 0.2529 (0.2472) | +0.0057 [+0.0032, +0.0082] | 0.490 | +0.0031 | 0.144 | REJECT |
| NQ | expansion | logistic | 1935 | 0.699 | 0.1116 (0.1215) | -0.0099 [-0.0161, -0.0043] | 0.653 | -0.0055 | 0.062 | ACCEPT_RESEARCH_ONLY |
| NQ | expansion | lightgbm | 1935 | 0.708 | 0.1135 (0.1215) | -0.0079 [-0.0137, -0.0024] | 0.629 | -0.0051 | 0.108 | ACCEPT_RESEARCH_ONLY |
| NQ | compression | logistic | 1935 | 0.725 | 0.1332 (0.1378) | -0.0045 [-0.0119, +0.0037] | 0.738 | -0.0114 | 0.393 | INCONCLUSIVE |
| NQ | compression | lightgbm | 1935 | 0.734 | 0.1285 (0.1378) | -0.0093 [-0.0148, -0.0035] | 0.744 | -0.0121 | 0.120 | ACCEPT_RESEARCH_ONLY |
| NQ | trend_day | logistic | 1935 | 0.590 | 0.1625 (0.1611) | +0.0014 [-0.0027, +0.0057] | 0.593 | -0.0017 | 0.139 | INCONCLUSIVE |
| NQ | trend_day | lightgbm | 1935 | 0.628 | 0.1582 (0.1611) | -0.0029 [-0.0064, +0.0011] | 0.587 | -0.0009 | 0.102 | INCONCLUSIVE |
| NQ | touch_prior_high | logistic | 1935 | 0.822 | 0.1676 (0.2452) | -0.0776 [-0.0872, -0.0670] | 0.813 | -0.0714 | 0.100 | ACCEPT_RESEARCH_ONLY |
| NQ | touch_prior_high | lightgbm | 1935 | 0.836 | 0.1631 (0.2452) | -0.0821 [-0.0906, -0.0730] | 0.814 | -0.0698 | 0.089 | ACCEPT_RESEARCH_ONLY |
| NQ | touch_prior_low | logistic | 1935 | 0.785 | 0.1848 (0.2448) | -0.0601 [-0.0692, -0.0499] | 0.806 | -0.0684 | 0.061 | ACCEPT_RESEARCH_ONLY |
| NQ | touch_prior_low | lightgbm | 1935 | 0.779 | 0.1870 (0.2448) | -0.0578 [-0.0667, -0.0483] | 0.798 | -0.0657 | 0.053 | ACCEPT_RESEARCH_ONLY |
| NQ | touch_prior_vwap | logistic | 1935 | 0.655 | 0.2043 (0.2195) | -0.0153 [-0.0229, -0.0081] | 0.657 | -0.0146 | 0.159 | ACCEPT_RESEARCH_ONLY |
| NQ | touch_prior_vwap | lightgbm | 1935 | 0.722 | 0.1893 (0.2195) | -0.0303 [-0.0381, -0.0226] | 0.754 | -0.0350 | 0.077 | ACCEPT_RESEARCH_ONLY |
| NQ | range_ge_points 100 | logistic | 1935 | 0.921 | 0.1035 (0.1387) | -0.0352 [-0.0508, -0.0212] | 0.369 | +0.0001 | 0.088 | INCONCLUSIVE |
| NQ | range_ge_points 100 | lightgbm | 1935 | 0.904 | 0.1284 (0.1387) | -0.0102 [-0.0219, +0.0016] | 0.763 | +0.0383 | 0.347 | INCONCLUSIVE |
| NQ | range_ge_points 200 | logistic | 1450 | 0.865 | 0.1270 (0.1582) | -0.0311 [-0.0582, -0.0088] | 0.700 | -0.0035 | 0.087 | ACCEPT_RESEARCH_ONLY |
| NQ | range_ge_points 200 | lightgbm | 1450 | 0.820 | 0.1631 (0.1582) | +0.0050 [-0.0151, +0.0249] | 0.711 | -0.0052 | 0.253 | INCONCLUSIVE |
| NQ | range_ge_points 350 | logistic | 485 | 0.788 | 0.1629 (0.2212) | -0.0584 [-0.0995, -0.0209] | 0.751 | -0.0219 | 0.112 | ACCEPT_RESEARCH_ONLY |
| NQ | range_ge_points 350 | lightgbm | 485 | 0.660 | 0.1934 (0.2212) | -0.0278 [-0.0604, +0.0067] | 0.743 | -0.0080 | 0.238 | INCONCLUSIVE |
| NQ | range_ge_points 500 | logistic | 242 | 0.661 | 0.1596 (0.1630) | -0.0034 [-0.0412, +0.0360] | 0.774 | -0.0219 | 0.075 | INCONCLUSIVE |
| NQ | range_ge_points 500 | lightgbm | 242 | 0.663 | 0.1568 (0.1630) | -0.0062 [-0.0222, +0.0083] | 0.725 | -0.0046 | 0.126 | INCONCLUSIVE |
| NQ | range_ge_atr 1.0×ATR | logistic | 1935 | 0.706 | 0.2140 (0.2419) | -0.0279 [-0.0406, -0.0160] | 0.676 | -0.0243 | 0.165 | ACCEPT_RESEARCH_ONLY |
| NQ | range_ge_atr 1.0×ATR | lightgbm | 1935 | 0.723 | 0.2076 (0.2419) | -0.0343 [-0.0450, -0.0234] | 0.699 | -0.0300 | 0.132 | ACCEPT_RESEARCH_ONLY |
| NQ | range_ge_atr 1.5×ATR | logistic | 1935 | 0.699 | 0.1116 (0.1215) | -0.0099 [-0.0161, -0.0043] | 0.653 | -0.0055 | 0.062 | ACCEPT_RESEARCH_ONLY |
| NQ | range_ge_atr 1.5×ATR | lightgbm | 1935 | 0.708 | 0.1135 (0.1215) | -0.0079 [-0.0137, -0.0024] | 0.629 | -0.0051 | 0.108 | ACCEPT_RESEARCH_ONLY |
| NQ | target_before_stop long 0.25x0.25 | logistic | 1931 | 0.503 | 0.2540 (0.2476) | +0.0065 [+0.0010, +0.0134] | 0.479 | +0.0001 | 0.394 | REJECT |
| NQ | target_before_stop long 0.25x0.25 | lightgbm | 1931 | 0.499 | 0.2474 (0.2476) | -0.0001 [-0.0015, +0.0012] | 0.475 | -0.0003 | 0.096 | INCONCLUSIVE |
| NQ | target_before_stop short 0.25x0.25 | logistic | 1931 | 0.525 | 0.2502 (0.2480) | +0.0021 [-0.0018, +0.0067] | 0.511 | -0.0007 | 0.269 | INCONCLUSIVE |
| NQ | target_before_stop short 0.25x0.25 | lightgbm | 1931 | 0.513 | 0.2464 (0.2480) | -0.0016 [-0.0034, +0.0002] | 0.528 | -0.0023 | 0.029 | INCONCLUSIVE |
| NQ | target_before_stop long 0.5x0.25 | logistic | 1931 | 0.540 | 0.1500 (0.1482) | +0.0018 [-0.0007, +0.0047] | 0.538 | +0.0025 | 0.117 | INCONCLUSIVE |
| NQ | target_before_stop long 0.5x0.25 | lightgbm | 1931 | 0.515 | 0.1501 (0.1482) | +0.0019 [+0.0004, +0.0037] | 0.521 | +0.0015 | 0.273 | REJECT |
| NQ | target_before_stop short 0.5x0.25 | logistic | 1931 | 0.556 | 0.1753 (0.1755) | -0.0002 [-0.0029, +0.0031] | 0.520 | +0.0012 | 0.135 | INCONCLUSIVE |
| NQ | target_before_stop short 0.5x0.25 | lightgbm | 1931 | 0.574 | 0.1734 (0.1755) | -0.0022 [-0.0039, -0.0004] | 0.535 | +0.0024 | 0.082 | INCONCLUSIVE |
| NQ | target_before_stop long 0.5x0.5 | logistic | 1931 | 0.577 | 0.1669 (0.1684) | -0.0015 [-0.0050, +0.0019] | 0.611 | -0.0046 | 0.078 | INCONCLUSIVE |
| NQ | target_before_stop long 0.5x0.5 | lightgbm | 1931 | 0.560 | 0.1677 (0.1684) | -0.0007 [-0.0029, +0.0016] | 0.592 | -0.0037 | 0.048 | INCONCLUSIVE |
| NQ | target_before_stop short 0.5x0.5 | logistic | 1931 | 0.598 | 0.1910 (0.1948) | -0.0038 [-0.0076, +0.0006] | 0.509 | +0.0007 | 0.143 | INCONCLUSIVE |
| NQ | target_before_stop short 0.5x0.5 | lightgbm | 1931 | 0.593 | 0.1908 (0.1948) | -0.0039 [-0.0071, -0.0008] | 0.537 | +0.0023 | 0.073 | INCONCLUSIVE |
| NQ | target_before_stop long 1.0x0.5 | logistic | 1931 | 0.602 | 0.0279 (0.0274) | +0.0005 [-0.0010, +0.0022] | 0.522 | +0.0015 | 0.005 | INCONCLUSIVE |
| NQ | target_before_stop long 1.0x0.5 | lightgbm | 1931 | 0.539 | 0.0281 (0.0274) | +0.0007 [-0.0010, +0.0027] | 0.585 | +0.0001 | 0.002 | INCONCLUSIVE |
| NQ | target_before_stop short 1.0x0.5 | logistic | 1931 | 0.587 | 0.0684 (0.0675) | +0.0009 [-0.0011, +0.0028] | 0.627 | +0.0000 | 0.009 | INCONCLUSIVE |
| NQ | target_before_stop short 1.0x0.5 | lightgbm | 1931 | 0.537 | 0.0682 (0.0675) | +0.0007 [-0.0004, +0.0019] | 0.610 | +0.0017 | 0.039 | INCONCLUSIVE |
| ES | direction | logistic | 1935 | 0.487 | 0.2519 (0.2485) | +0.0034 [+0.0012, +0.0057] | 0.511 | +0.0007 | 0.101 | REJECT |
| ES | direction | lightgbm | 1935 | 0.478 | 0.2511 (0.2485) | +0.0026 [+0.0011, +0.0043] | 0.519 | +0.0000 | 0.115 | REJECT |
| ES | expansion | logistic | 1935 | 0.746 | 0.1103 (0.1294) | -0.0191 [-0.0284, -0.0104] | 0.699 | -0.0103 | 0.109 | ACCEPT_RESEARCH_ONLY |
| ES | expansion | lightgbm | 1935 | 0.742 | 0.1106 (0.1294) | -0.0188 [-0.0273, -0.0112] | 0.684 | -0.0102 | 0.031 | ACCEPT_RESEARCH_ONLY |
| ES | compression | logistic | 1935 | 0.769 | 0.1363 (0.1484) | -0.0121 [-0.0225, +0.0006] | 0.776 | -0.0190 | 0.230 | INCONCLUSIVE |
| ES | compression | lightgbm | 1935 | 0.758 | 0.1338 (0.1484) | -0.0147 [-0.0210, -0.0081] | 0.768 | -0.0186 | 0.314 | ACCEPT_RESEARCH_ONLY |
| ES | trend_day | logistic | 1935 | 0.610 | 0.1562 (0.1564) | -0.0002 [-0.0042, +0.0041] | 0.635 | -0.0046 | 0.200 | INCONCLUSIVE |
| ES | trend_day | lightgbm | 1935 | 0.621 | 0.1575 (0.1564) | +0.0011 [-0.0031, +0.0063] | 0.643 | -0.0042 | 0.144 | INCONCLUSIVE |
| ES | touch_prior_high | logistic | 1935 | 0.808 | 0.1768 (0.2475) | -0.0707 [-0.0801, -0.0605] | 0.808 | -0.0703 | 0.112 | ACCEPT_RESEARCH_ONLY |
| ES | touch_prior_high | lightgbm | 1935 | 0.809 | 0.1761 (0.2475) | -0.0714 [-0.0811, -0.0613] | 0.821 | -0.0776 | 0.077 | ACCEPT_RESEARCH_ONLY |
| ES | touch_prior_low | logistic | 1935 | 0.800 | 0.1777 (0.2447) | -0.0669 [-0.0763, -0.0577] | 0.793 | -0.0631 | 0.059 | ACCEPT_RESEARCH_ONLY |
| ES | touch_prior_low | lightgbm | 1935 | 0.785 | 0.1836 (0.2447) | -0.0610 [-0.0705, -0.0519] | 0.790 | -0.0603 | 0.061 | ACCEPT_RESEARCH_ONLY |
| ES | touch_prior_vwap | logistic | 1935 | 0.640 | 0.2001 (0.2115) | -0.0114 [-0.0173, -0.0057] | 0.655 | -0.0119 | 0.074 | ACCEPT_RESEARCH_ONLY |
| ES | touch_prior_vwap | lightgbm | 1935 | 0.701 | 0.1883 (0.2115) | -0.0232 [-0.0311, -0.0151] | 0.756 | -0.0321 | 0.105 | ACCEPT_RESEARCH_ONLY |
| ES | range_ge_points 25 | logistic | 1935 | 0.888 | 0.1251 (0.1743) | -0.0491 [-0.0708, -0.0302] | 0.593 | +0.0002 | 0.079 | INCONCLUSIVE |
| ES | range_ge_points 25 | lightgbm | 1935 | 0.870 | 0.1383 (0.1743) | -0.0360 [-0.0557, -0.0184] | 0.732 | +0.0376 | 0.129 | INCONCLUSIVE |
| ES | range_ge_points 50 | logistic | 1695 | 0.923 | 0.0939 (0.1429) | -0.0490 [-0.0731, -0.0295] | 0.767 | -0.0404 | 0.130 | ACCEPT_RESEARCH_ONLY |
| ES | range_ge_points 50 | lightgbm | 1695 | 0.898 | 0.1181 (0.1429) | -0.0248 [-0.0427, -0.0079] | 0.738 | -0.0294 | 0.336 | ACCEPT_RESEARCH_ONLY |
| ES | range_ge_points 100 | logistic | 1453 | 0.844 | 0.0707 (0.0849) | -0.0142 [-0.0292, -0.0028] | 0.747 | -0.0235 | 0.168 | ACCEPT_RESEARCH_ONLY |
| ES | range_ge_points 100 | lightgbm | 1453 | 0.809 | 0.0811 (0.0849) | -0.0038 [-0.0121, +0.0040] | 0.707 | -0.0185 | 0.046 | INCONCLUSIVE |
| ES | range_ge_points 150 | logistic | 485 | 0.534 | 0.0564 (0.0384) | +0.0180 [+0.0001, +0.0408] | 0.680 | -0.0031 | 0.019 | REJECT |
| ES | range_ge_points 150 | lightgbm | 485 | 0.411 | 0.0431 (0.0384) | +0.0047 [+0.0008, +0.0085] | 0.603 | -0.0047 | 0.011 | REJECT |
| ES | range_ge_atr 1.0×ATR | logistic | 1935 | 0.746 | 0.1996 (0.2415) | -0.0419 [-0.0551, -0.0286] | 0.714 | -0.0340 | 0.107 | ACCEPT_RESEARCH_ONLY |
| ES | range_ge_atr 1.0×ATR | lightgbm | 1935 | 0.750 | 0.1967 (0.2415) | -0.0448 [-0.0566, -0.0333] | 0.732 | -0.0397 | 0.099 | ACCEPT_RESEARCH_ONLY |
| ES | range_ge_atr 1.5×ATR | logistic | 1935 | 0.745 | 0.1106 (0.1298) | -0.0191 [-0.0285, -0.0105] | 0.699 | -0.0103 | 0.026 | ACCEPT_RESEARCH_ONLY |
| ES | range_ge_atr 1.5×ATR | lightgbm | 1935 | 0.739 | 0.1113 (0.1298) | -0.0185 [-0.0268, -0.0109] | 0.691 | -0.0097 | 0.060 | ACCEPT_RESEARCH_ONLY |
| ES | target_before_stop long 0.25x0.25 | logistic | 1931 | 0.518 | 0.2472 (0.2463) | +0.0009 [-0.0016, +0.0036] | 0.479 | +0.0012 | 0.079 | INCONCLUSIVE |
| ES | target_before_stop long 0.25x0.25 | lightgbm | 1931 | 0.508 | 0.2462 (0.2463) | -0.0001 [-0.0017, +0.0015] | 0.500 | +0.0011 | 0.060 | INCONCLUSIVE |
| ES | target_before_stop short 0.25x0.25 | logistic | 1931 | 0.538 | 0.2490 (0.2480) | +0.0010 [-0.0025, +0.0047] | 0.503 | +0.0014 | 0.282 | INCONCLUSIVE |
| ES | target_before_stop short 0.25x0.25 | lightgbm | 1931 | 0.530 | 0.2469 (0.2480) | -0.0011 [-0.0039, +0.0015] | 0.481 | +0.0008 | 0.045 | INCONCLUSIVE |
| ES | target_before_stop long 0.5x0.25 | logistic | 1931 | 0.587 | 0.1444 (0.1449) | -0.0005 [-0.0031, +0.0021] | 0.568 | +0.0007 | 0.060 | INCONCLUSIVE |
| ES | target_before_stop long 0.5x0.25 | lightgbm | 1931 | 0.584 | 0.1455 (0.1449) | +0.0006 [-0.0017, +0.0033] | 0.534 | +0.0014 | 0.286 | INCONCLUSIVE |
| ES | target_before_stop short 0.5x0.25 | logistic | 1931 | 0.566 | 0.1697 (0.1708) | -0.0012 [-0.0037, +0.0014] | 0.569 | +0.0002 | 0.042 | INCONCLUSIVE |
| ES | target_before_stop short 0.5x0.25 | lightgbm | 1931 | 0.548 | 0.1703 (0.1708) | -0.0005 [-0.0026, +0.0016] | 0.559 | +0.0061 | 0.082 | INCONCLUSIVE |
| ES | target_before_stop long 0.5x0.5 | logistic | 1931 | 0.635 | 0.1594 (0.1661) | -0.0067 [-0.0106, -0.0030] | 0.644 | -0.0082 | 0.083 | ACCEPT_RESEARCH_ONLY |
| ES | target_before_stop long 0.5x0.5 | lightgbm | 1931 | 0.634 | 0.1607 (0.1661) | -0.0054 [-0.0096, -0.0015] | 0.601 | -0.0045 | 0.093 | ACCEPT_RESEARCH_ONLY |
| ES | target_before_stop short 0.5x0.5 | logistic | 1931 | 0.611 | 0.1860 (0.1911) | -0.0051 [-0.0084, -0.0018] | 0.570 | -0.0016 | 0.011 | ACCEPT_RESEARCH_ONLY |
| ES | target_before_stop short 0.5x0.5 | lightgbm | 1931 | 0.581 | 0.1878 (0.1911) | -0.0033 [-0.0062, -0.0003] | 0.570 | +0.0016 | 0.059 | INCONCLUSIVE |
| ES | target_before_stop long 1.0x0.5 | logistic | 1931 | 0.610 | 0.0368 (0.0347) | +0.0022 [-0.0005, +0.0056] | 0.585 | -0.0015 | 0.003 | INCONCLUSIVE |
| ES | target_before_stop long 1.0x0.5 | lightgbm | 1931 | 0.567 | 0.0392 (0.0347) | +0.0045 [-0.0002, +0.0104] | 0.451 | +0.0018 | 0.003 | INCONCLUSIVE |
| ES | target_before_stop short 1.0x0.5 | logistic | 1931 | 0.593 | 0.0699 (0.0687) | +0.0012 [-0.0010, +0.0041] | 0.651 | +0.0006 | 0.006 | INCONCLUSIVE |
| ES | target_before_stop short 1.0x0.5 | lightgbm | 1931 | 0.569 | 0.0687 (0.0687) | +0.0001 [-0.0010, +0.0011] | 0.513 | +0.0051 | 0.034 | INCONCLUSIVE |

## Range quantiles

- NQ: dev pinball 25.32 vs baseline 27.18, Δ -1.86 [-4.03, +0.23]; coverage {'coverage_q50': 0.3452, 'coverage_q80': 0.5959, 'coverage_q90': 0.7332}; holdout Δ -5.77; INCONCLUSIVE
- ES: dev pinball 6.63 vs baseline 8.10, Δ -1.47 [-2.09, -0.89]; coverage {'coverage_q50': 0.3922, 'coverage_q80': 0.6728, 'coverage_q90': 0.7705}; holdout Δ -2.36; ACCEPT_RESEARCH_ONLY

## Target-before-stop economics (trade only when p > break-even)

| Root | Side | Geometry (ATR) | Model | Dev trades | Dev mean R [CI] | Dev always-trade R | Hold trades | Hold mean R [CI] |
|---|---|---|---|---|---|---|---|---|
| NQ | long | 0.25x0.25 | logistic | 182 | -0.088 [-0.228, 0.053] | -0.019 [-0.062, 0.023] | 17 | -0.366 [-0.809, 0.076] |
| NQ | long | 0.25x0.25 | lightgbm | 87 | -0.027 [-0.227, 0.172] | -0.019 [-0.062, 0.023] | 3 | 0.993 [0.990, 0.995] |
| NQ | short | 0.25x0.25 | logistic | 151 | 0.032 [-0.126, 0.190] | -0.044 [-0.086, -0.001] | 237 | -0.050 [-0.174, 0.074] |
| NQ | short | 0.25x0.25 | lightgbm | 49 | 0.099 [-0.178, 0.376] | -0.044 [-0.086, -0.001] | 161 | 0.108 [-0.042, 0.259] |
| NQ | long | 0.5x0.25 | logistic | 61 | -0.323 [-0.633, -0.014] | -0.009 [-0.063, 0.045] | 32 | -0.276 [-0.713, 0.162] |
| NQ | long | 0.5x0.25 | lightgbm | 40 | -0.389 [-0.744, -0.034] | -0.009 [-0.063, 0.045] | 8 | -0.039 [-0.951, 0.873] |
| NQ | short | 0.5x0.25 | logistic | 102 | 0.117 [-0.160, 0.394] | -0.042 [-0.097, 0.014] | 57 | -0.226 [-0.552, 0.100] |
| NQ | short | 0.5x0.25 | lightgbm | 53 | -0.125 [-0.491, 0.241] | -0.042 [-0.097, 0.014] | 91 | -0.067 [-0.329, 0.195] |
| NQ | long | 0.5x0.5 | logistic | 40 | -0.138 [-0.423, 0.147] | -0.008 [-0.042, 0.026] | 25 | 0.048 [-0.333, 0.428] |
| NQ | long | 0.5x0.5 | lightgbm | 9 | -0.346 [-0.999, 0.307] | -0.008 [-0.042, 0.026] | 10 | 0.396 [-0.202, 0.995] |
| NQ | short | 0.5x0.5 | logistic | 47 | 0.022 [-0.248, 0.291] | -0.023 [-0.057, 0.011] | 0 | n/a |
| NQ | short | 0.5x0.5 | lightgbm | 7 | -0.259 [-0.851, 0.332] | -0.023 [-0.057, 0.011] | 12 | -0.394 [-0.881, 0.094] |
| NQ | long | 1.0x0.5 | logistic | 8 | -0.209 [-1.084, 0.667] | -0.003 [-0.040, 0.034] | 2 | -0.382 [-1.597, 0.834] |
| NQ | long | 1.0x0.5 | lightgbm | 11 | 0.784 [0.093, 1.474] | -0.003 [-0.040, 0.034] | 1 | 1.224 |
| NQ | short | 1.0x0.5 | logistic | 22 | 0.017 [-0.503, 0.536] | -0.015 [-0.054, 0.025] | 3 | -0.034 [-1.384, 1.317] |
| NQ | short | 1.0x0.5 | lightgbm | 4 | -0.751 [-1.251, -0.250] | -0.015 [-0.054, 0.025] | 7 | -0.318 [-1.224, 0.587] |
| ES | long | 0.25x0.25 | logistic | 119 | -0.091 [-0.266, 0.085] | -0.098 [-0.140, -0.056] | 61 | -0.049 [-0.298, 0.199] |
| ES | long | 0.25x0.25 | lightgbm | 121 | -0.013 [-0.188, 0.162] | -0.098 [-0.140, -0.056] | 180 | -0.005 [-0.145, 0.134] |
| ES | short | 0.25x0.25 | logistic | 375 | -0.130 [-0.230, -0.030] | -0.102 [-0.144, -0.060] | 224 | -0.089 [-0.217, 0.040] |
| ES | short | 0.25x0.25 | lightgbm | 200 | -0.069 [-0.205, 0.066] | -0.102 [-0.144, -0.060] | 172 | -0.140 [-0.287, 0.007] |
| ES | long | 0.5x0.25 | logistic | 55 | -0.037 [-0.402, 0.328] | -0.091 [-0.144, -0.037] | 24 | -0.328 [-0.834, 0.178] |
| ES | long | 0.5x0.25 | lightgbm | 82 | -0.119 [-0.397, 0.158] | -0.091 [-0.144, -0.037] | 2 | -1.027 [-1.038, -1.016] |
| ES | short | 0.5x0.25 | logistic | 84 | -0.101 [-0.404, 0.202] | -0.113 [-0.168, -0.058] | 115 | -0.084 [-0.330, 0.161] |
| ES | short | 0.5x0.25 | lightgbm | 55 | -0.201 [-0.542, 0.141] | -0.113 [-0.168, -0.058] | 171 | -0.222 [-0.410, -0.034] |
| ES | long | 0.5x0.5 | logistic | 42 | 0.004 [-0.282, 0.289] | -0.042 [-0.076, -0.009] | 32 | 0.050 [-0.269, 0.369] |
| ES | long | 0.5x0.5 | lightgbm | 37 | 0.252 [-0.033, 0.536] | -0.042 [-0.076, -0.009] | 8 | 0.127 [-0.558, 0.813] |
| ES | short | 0.5x0.5 | logistic | 29 | -0.260 [-0.569, 0.049] | -0.057 [-0.090, -0.023] | 9 | -0.357 [-1.011, 0.296] |
| ES | short | 0.5x0.5 | lightgbm | 8 | 0.104 [-0.448, 0.656] | -0.057 [-0.090, -0.023] | 27 | -0.147 [-0.482, 0.188] |
| ES | long | 1.0x0.5 | logistic | 12 | -0.299 [-0.900, 0.301] | -0.039 [-0.076, -0.002] | 8 | 0.623 [-0.413, 1.658] |
| ES | long | 1.0x0.5 | lightgbm | 17 | -0.386 [-0.914, 0.143] | -0.039 [-0.076, -0.002] | 3 | 0.395 [-0.988, 1.779] |
| ES | short | 1.0x0.5 | logistic | 12 | -0.524 [-1.083, 0.035] | -0.057 [-0.096, -0.018] | 10 | -0.714 [-1.108, -0.319] |
| ES | short | 1.0x0.5 | lightgbm | 4 | -0.501 [-1.256, 0.253] | -0.057 [-0.096, -0.018] | 12 | -0.252 [-0.813, 0.308] |

## Feature-family ablation (logistic, Brier Δ vs baseline)

| Root | Objective | Features | Dev Δ [CI] | Hold Δ | Verdict |
|---|---|---|---|---|---|
| NQ | direction | price_only | +0.0116 [+0.0064, +0.0173] | +0.0024 | REJECT |
| NQ | direction | intraday | +0.0053 [+0.0024, +0.0083] | +0.0025 | REJECT |
| NQ | direction | volatility | +0.0163 [+0.0092, +0.0243] | +0.0020 | REJECT |
| NQ | direction | rates_credit | +0.0059 [+0.0028, +0.0093] | +0.0020 | REJECT |
| NQ | direction | positioning | +0.0104 [+0.0061, +0.0152] | +0.0019 | REJECT |
| NQ | direction | filings | +0.0118 [+0.0066, +0.0175] | +0.0024 | REJECT |
| NQ | expansion | price_only | -0.0081 [-0.0140, -0.0023] | -0.0053 | ACCEPT_RESEARCH_ONLY |
| NQ | expansion | intraday | -0.0099 [-0.0161, -0.0043] | -0.0055 | ACCEPT_RESEARCH_ONLY |
| NQ | expansion | volatility | -0.0106 [-0.0172, -0.0045] | -0.0051 | ACCEPT_RESEARCH_ONLY |
| NQ | expansion | rates_credit | -0.0090 [-0.0144, -0.0031] | -0.0056 | ACCEPT_RESEARCH_ONLY |
| NQ | expansion | positioning | -0.0072 [-0.0144, -0.0001] | -0.0057 | ACCEPT_RESEARCH_ONLY |
| NQ | expansion | filings | -0.0082 [-0.0137, -0.0025] | -0.0051 | ACCEPT_RESEARCH_ONLY |
| ES | direction | price_only | +0.0023 [+0.0007, +0.0042] | +0.0012 | REJECT |
| ES | direction | intraday | +0.0034 [+0.0012, +0.0057] | +0.0007 | REJECT |
| ES | direction | volatility | +0.0066 [+0.0036, +0.0099] | +0.0016 | REJECT |
| ES | direction | rates_credit | +0.0060 [+0.0028, +0.0093] | +0.0005 | REJECT |
| ES | direction | positioning | +0.0018 [-0.0004, +0.0041] | +0.0029 | INCONCLUSIVE |
| ES | direction | filings | +0.0033 [+0.0012, +0.0055] | +0.0013 | REJECT |
| ES | expansion | price_only | -0.0165 [-0.0247, -0.0090] | -0.0099 | ACCEPT_RESEARCH_ONLY |
| ES | expansion | intraday | -0.0191 [-0.0284, -0.0104] | -0.0103 | ACCEPT_RESEARCH_ONLY |
| ES | expansion | volatility | -0.0215 [-0.0315, -0.0125] | -0.0102 | ACCEPT_RESEARCH_ONLY |
| ES | expansion | rates_credit | -0.0163 [-0.0245, -0.0087] | -0.0105 | ACCEPT_RESEARCH_ONLY |
| ES | expansion | positioning | -0.0167 [-0.0254, -0.0089] | -0.0104 | ACCEPT_RESEARCH_ONLY |
| ES | expansion | filings | -0.0166 [-0.0247, -0.0091] | -0.0097 | ACCEPT_RESEARCH_ONLY |
