# Phase 3V — zero-cost futures research (Yahoo NQ=F / ES=F)

Generated 2026-11-09T04:11:41.163019+00:00. Spend: **$0**. Scope: retrospective walk-forward on continuous front-month proxies; not raw contracts, not order flow, not forward evidence. NO_PROMOTION / NO_TRADE.

## NQ

Sessions 2000-09-18 → 2026-11-05: 6047 usable after excluding 462 near 66 Databento volume rolls.

| Task | Config | Dev n | Dev Brier model | Dev Brier baseline | Dev Δ [95% CI] | Dev AUC | Holdout Δ | Holdout AUC | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| direction_next_settle_up | price_logit | 3578 | 0.25496 | 0.24879 | +0.00617 [+0.00395, +0.00828] | 0.4813 | +0.00385 | 0.5090 | REJECT |
| direction_next_settle_up | all_logit | 3022 | 0.25596 | 0.24842 | +0.00754 [+0.00436, +0.01093] | 0.4861 | +0.00139 | 0.4878 | REJECT |
| direction_next_settle_up | all_lgbm | 3022 | 0.25065 | 0.24842 | +0.00223 [+0.00022, +0.00421] | 0.4926 | +0.00089 | 0.5018 | REJECT |
| direction_next_settle_up | price+volatility_logit | 3578 | 0.25463 | 0.24879 | +0.00584 [+0.00351, +0.00820] | 0.4818 | +0.00290 | 0.5048 | REJECT |
| direction_next_settle_up | price+rates_credit_logit | 3076 | 0.25741 | 0.24829 | +0.00913 [+0.00503, +0.01370] | 0.4822 | +0.00209 | 0.5041 | REJECT |
| direction_next_settle_up | price+positioning_logit | 3022 | 0.25466 | 0.24842 | +0.00624 [+0.00322, +0.00917] | 0.4825 | +0.00221 | 0.5041 | REJECT |
| direction_next_settle_up | price+filings_logit | 3578 | 0.25429 | 0.24879 | +0.00549 [+0.00347, +0.00731] | 0.4771 | +0.00359 | 0.5088 | REJECT |
| compression_next_range_lt_0.6atr | price_logit | 3578 | 0.12174 | 0.12219 | -0.00045 [-0.00741, +0.00694] | 0.7308 | -0.01100 | 0.7311 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | all_logit | 3022 | 0.12569 | 0.12505 | +0.00063 [-0.00822, +0.01036] | 0.7446 | -0.01533 | 0.7791 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | all_lgbm | 3022 | 0.11777 | 0.12505 | -0.00728 [-0.01195, -0.00224] | 0.7191 | -0.01503 | 0.7680 | ACCEPT_RESEARCH_ONLY |
| compression_next_range_lt_0.6atr | price+volatility_logit | 3578 | 0.12989 | 0.12219 | +0.00770 [-0.00195, +0.01905] | 0.7349 | -0.01328 | 0.7777 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | price+rates_credit_logit | 3076 | 0.12510 | 0.12553 | -0.00042 [-0.00823, +0.00797] | 0.7411 | -0.01108 | 0.7329 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | price+positioning_logit | 3022 | 0.12478 | 0.12505 | -0.00027 [-0.00804, +0.00807] | 0.7265 | -0.01267 | 0.7395 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | price+filings_logit | 3578 | 0.12158 | 0.12219 | -0.00061 [-0.00756, +0.00665] | 0.7297 | -0.01072 | 0.7292 | INCONCLUSIVE |
| range_ge_100pts | price_logit | 2662 | 0.06516 | 0.09485 | -0.02969 [-0.04363, -0.01779] | 0.9626 | -0.00011 | 0.8656 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | all_logit | 2358 | 0.06906 | 0.10324 | -0.03418 [-0.05029, -0.02142] | 0.9606 | -0.00014 | 0.8460 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | all_lgbm | 2358 | 0.09820 | 0.10324 | -0.00504 [-0.01318, +0.00318] | 0.9441 | -0.00008 | 0.8333 | INCONCLUSIVE |
| range_ge_100pts | price+volatility_logit | 2662 | 0.06419 | 0.09485 | -0.03065 [-0.04467, -0.01879] | 0.9634 | -0.00012 | 0.8747 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | price+rates_credit_logit | 2412 | 0.07188 | 0.10427 | -0.03239 [-0.04744, -0.01943] | 0.9595 | -0.00011 | 0.8451 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | price+positioning_logit | 2358 | 0.06976 | 0.10324 | -0.03349 [-0.04916, -0.02094] | 0.9618 | -0.00012 | 0.8409 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | price+filings_logit | 2662 | 0.06646 | 0.09485 | -0.02839 [-0.04256, -0.01659] | 0.9603 | -0.00011 | 0.8633 | ACCEPT_RESEARCH_ONLY |
| range_ge_200pts | price_logit | 1755 | 0.12234 | 0.15222 | -0.02988 [-0.04911, -0.01318] | 0.8887 | -0.01179 | 0.8196 | ACCEPT_RESEARCH_ONLY |
| range_ge_200pts | all_logit | 1726 | 0.13134 | 0.15428 | -0.02294 [-0.04116, -0.00708] | 0.8718 | -0.01343 | 0.8227 | ACCEPT_RESEARCH_ONLY |
| range_ge_200pts | all_lgbm | 1726 | 0.15177 | 0.15428 | -0.00250 [-0.01656, +0.01236] | 0.8490 | -0.01073 | 0.8238 | INCONCLUSIVE |
| range_ge_200pts | price+volatility_logit | 1755 | 0.11975 | 0.15222 | -0.03248 [-0.05213, -0.01577] | 0.8940 | -0.01347 | 0.8240 | ACCEPT_RESEARCH_ONLY |
| range_ge_200pts | price+rates_credit_logit | 1755 | 0.13281 | 0.15222 | -0.01942 [-0.03654, -0.00520] | 0.8780 | -0.01093 | 0.8150 | ACCEPT_RESEARCH_ONLY |
| range_ge_200pts | price+positioning_logit | 1726 | 0.12829 | 0.15428 | -0.02599 [-0.04512, -0.00907] | 0.8817 | -0.01234 | 0.8189 | ACCEPT_RESEARCH_ONLY |
| range_ge_200pts | price+filings_logit | 1755 | 0.12302 | 0.15222 | -0.02921 [-0.04850, -0.01224] | 0.8879 | -0.01180 | 0.8192 | ACCEPT_RESEARCH_ONLY |
| range_ge_350pts | price_logit | 879 | 0.15211 | 0.18858 | -0.03647 [-0.06268, -0.01362] | 0.7409 | -0.03520 | 0.7831 | ACCEPT_RESEARCH_ONLY |
| range_ge_350pts | all_logit | 879 | 0.15956 | 0.18858 | -0.02903 [-0.05632, -0.00505] | 0.7246 | -0.04310 | 0.7964 | ACCEPT_RESEARCH_ONLY |
| range_ge_350pts | all_lgbm | 879 | 0.17729 | 0.18858 | -0.01130 [-0.03064, +0.00617] | 0.5477 | -0.01120 | 0.7783 | INCONCLUSIVE |
| range_ge_350pts | price+volatility_logit | 879 | 0.13758 | 0.18858 | -0.05101 [-0.07877, -0.02651] | 0.7850 | -0.04564 | 0.7906 | ACCEPT_RESEARCH_ONLY |
| range_ge_350pts | price+rates_credit_logit | 879 | 0.15610 | 0.18858 | -0.03249 [-0.05998, -0.00880] | 0.7443 | -0.03393 | 0.7431 | ACCEPT_RESEARCH_ONLY |
| range_ge_350pts | price+positioning_logit | 879 | 0.16090 | 0.18858 | -0.02769 [-0.05644, -0.00301] | 0.6755 | -0.03329 | 0.7896 | ACCEPT_RESEARCH_ONLY |
| range_ge_350pts | price+filings_logit | 879 | 0.14993 | 0.18858 | -0.03866 [-0.06896, -0.01097] | 0.7592 | -0.03577 | 0.7839 | ACCEPT_RESEARCH_ONLY |
| range_ge_500pts | price_logit | 438 | 0.08410 | 0.08899 | -0.00489 [-0.02519, +0.01213] | 0.6261 | -0.03339 | 0.8070 | INCONCLUSIVE |
| range_ge_500pts | all_logit | 438 | 0.08807 | 0.08899 | -0.00092 [-0.01607, +0.01270] | 0.4742 | -0.03198 | 0.8213 | INCONCLUSIVE |
| range_ge_500pts | all_lgbm | 438 | 0.09579 | 0.08899 | +0.00680 [+0.00007, +0.01358] | 0.3627 | -0.00821 | 0.7850 | REJECT |
| range_ge_500pts | price+volatility_logit | 438 | 0.08226 | 0.08899 | -0.00674 [-0.02576, +0.00914] | 0.6199 | -0.03526 | 0.8152 | INCONCLUSIVE |
| range_ge_500pts | price+rates_credit_logit | 438 | 0.08746 | 0.08899 | -0.00153 [-0.02021, +0.01626] | 0.5147 | -0.03793 | 0.8148 | INCONCLUSIVE |
| range_ge_500pts | price+positioning_logit | 438 | 0.08740 | 0.08899 | -0.00159 [-0.02158, +0.01553] | 0.5653 | -0.02220 | 0.7944 | INCONCLUSIVE |
| range_ge_500pts | price+filings_logit | 438 | 0.08469 | 0.08899 | -0.00430 [-0.02265, +0.01150] | 0.5824 | -0.03429 | 0.8092 | INCONCLUSIVE |

### Feature-family increment over price-only logistic (Brier Δ, matched sessions; negative = family helps)

| Task | Config | Dev n | Dev Δ [95% CI] | Holdout n | Holdout Δ [95% CI] | Verdict |
|---|---|---|---|---|---|---|
| direction_next_settle_up | all_logit | 3022 | +0.00204 [-0.00132, +0.00539] | 580 | -0.00256 [-0.00689, +0.00125] | NO_DETECTABLE_INCREMENT |
| direction_next_settle_up | all_lgbm | 3022 | -0.00327 [-0.00562, -0.00118] | 580 | -0.00305 [-0.00787, +0.00143] | FAMILY_HELPS |
| direction_next_settle_up | price+volatility_logit | 3578 | -0.00033 [-0.00129, +0.00055] | 629 | -0.00095 [-0.00209, +0.00010] | NO_DETECTABLE_INCREMENT |
| direction_next_settle_up | price+rates_credit_logit | 3076 | +0.00368 [-0.00049, +0.00806] | 629 | -0.00176 [-0.00552, +0.00169] | NO_DETECTABLE_INCREMENT |
| direction_next_settle_up | price+positioning_logit | 3022 | +0.00075 [-0.00122, +0.00281] | 580 | -0.00173 [-0.00418, +0.00055] | NO_DETECTABLE_INCREMENT |
| direction_next_settle_up | price+filings_logit | 3578 | -0.00068 [-0.00197, +0.00048] | 629 | -0.00026 [-0.00207, +0.00164] | NO_DETECTABLE_INCREMENT |
| compression_next_range_lt_0.6atr | all_logit | 3022 | +0.00114 [-0.00470, +0.00709] | 580 | -0.00567 [-0.01064, -0.00167] | NO_DETECTABLE_INCREMENT |
| compression_next_range_lt_0.6atr | all_lgbm | 3022 | -0.00677 [-0.01474, +0.00050] | 580 | -0.00537 [-0.01095, +0.00050] | NO_DETECTABLE_INCREMENT |
| compression_next_range_lt_0.6atr | price+volatility_logit | 3578 | +0.00814 [+0.00176, +0.01465] | 629 | -0.00228 [-0.00609, +0.00141] | FAMILY_HURTS |
| compression_next_range_lt_0.6atr | price+rates_credit_logit | 3076 | +0.00019 [-0.00350, +0.00361] | 629 | -0.00008 [-0.00308, +0.00429] | NO_DETECTABLE_INCREMENT |
| compression_next_range_lt_0.6atr | price+positioning_logit | 3022 | +0.00024 [-0.00384, +0.00417] | 580 | -0.00302 [-0.00449, -0.00139] | NO_DETECTABLE_INCREMENT |
| compression_next_range_lt_0.6atr | price+filings_logit | 3578 | -0.00016 [-0.00055, +0.00020] | 629 | +0.00028 [-0.00047, +0.00104] | NO_DETECTABLE_INCREMENT |
| range_ge_100pts | all_logit | 2358 | -0.00113 [-0.00299, +0.00085] | 397 | -0.00001 [-0.00001, -0.00000] | NO_DETECTABLE_INCREMENT |
| range_ge_100pts | all_lgbm | 2358 | +0.02801 [+0.01737, +0.04205] | 397 | +0.00005 [+0.00001, +0.00007] | FAMILY_HURTS |
| range_ge_100pts | price+volatility_logit | 2662 | -0.00097 [-0.00178, -0.00027] | 440 | -0.00001 [-0.00001, -0.00000] | FAMILY_HELPS |
| range_ge_100pts | price+rates_credit_logit | 2412 | +0.00039 [-0.00108, +0.00215] | 440 | -0.00000 [-0.00001, +0.00000] | NO_DETECTABLE_INCREMENT |
| range_ge_100pts | price+positioning_logit | 2358 | -0.00044 [-0.00166, +0.00084] | 397 | +0.00001 [+0.00000, +0.00002] | NO_DETECTABLE_INCREMENT |
| range_ge_100pts | price+filings_logit | 2662 | +0.00130 [-0.00006, +0.00294] | 440 | +0.00000 [+0.00000, +0.00000] | NO_DETECTABLE_INCREMENT |
| range_ge_200pts | all_logit | 1726 | +0.00727 [-0.00005, +0.01575] | 580 | -0.00128 [-0.00321, +0.00056] | NO_DETECTABLE_INCREMENT |
| range_ge_200pts | all_lgbm | 1726 | +0.02770 [+0.00740, +0.05030] | 580 | +0.00141 [-0.00819, +0.00976] | FAMILY_HURTS |
| range_ge_200pts | price+volatility_logit | 1755 | -0.00259 [-0.00635, +0.00086] | 629 | -0.00168 [-0.00270, -0.00073] | NO_DETECTABLE_INCREMENT |
| range_ge_200pts | price+rates_credit_logit | 1755 | +0.01046 [+0.00287, +0.01976] | 629 | +0.00085 [+0.00001, +0.00178] | FAMILY_HURTS |
| range_ge_200pts | price+positioning_logit | 1726 | +0.00422 [+0.00062, +0.00803] | 580 | -0.00020 [-0.00226, +0.00154] | FAMILY_HURTS |
| range_ge_200pts | price+filings_logit | 1755 | +0.00068 [-0.00004, +0.00152] | 629 | -0.00001 [-0.00010, +0.00004] | NO_DETECTABLE_INCREMENT |
| range_ge_350pts | all_logit | 879 | +0.00745 [-0.00328, +0.01704] | 580 | -0.00837 [-0.01512, -0.00206] | NO_DETECTABLE_INCREMENT |
| range_ge_350pts | all_lgbm | 879 | +0.02518 [+0.01287, +0.03816] | 580 | +0.02352 [+0.00955, +0.04013] | FAMILY_HURTS |
| range_ge_350pts | price+volatility_logit | 879 | -0.01453 [-0.02812, -0.00467] | 629 | -0.01043 [-0.01803, -0.00324] | FAMILY_HELPS |
| range_ge_350pts | price+rates_credit_logit | 879 | +0.00399 [-0.00390, +0.01037] | 629 | +0.00127 [-0.00030, +0.00288] | NO_DETECTABLE_INCREMENT |
| range_ge_350pts | price+positioning_logit | 879 | +0.00879 [+0.00328, +0.01616] | 580 | +0.00144 [+0.00001, +0.00317] | FAMILY_HURTS |
| range_ge_350pts | price+filings_logit | 879 | -0.00218 [-0.01826, +0.01143] | 629 | -0.00056 [-0.00120, +0.00010] | NO_DETECTABLE_INCREMENT |
| range_ge_500pts | all_logit | 438 | +0.00397 [-0.00148, +0.01067] | 580 | -0.00300 [-0.01451, +0.00810] | NO_DETECTABLE_INCREMENT |
| range_ge_500pts | all_lgbm | 438 | +0.01170 [-0.00704, +0.03376] | 580 | +0.02077 [-0.00057, +0.04447] | NO_DETECTABLE_INCREMENT |
| range_ge_500pts | price+volatility_logit | 438 | -0.00184 [-0.00397, +0.00013] | 629 | -0.00187 [-0.00840, +0.00467] | NO_DETECTABLE_INCREMENT |
| range_ge_500pts | price+rates_credit_logit | 438 | +0.00336 [-0.00061, +0.00800] | 629 | -0.00454 [-0.00969, +0.00072] | NO_DETECTABLE_INCREMENT |
| range_ge_500pts | price+positioning_logit | 438 | +0.00330 [+0.00145, +0.00562] | 580 | +0.00677 [-0.00239, +0.01807] | FAMILY_HURTS |
| range_ge_500pts | price+filings_logit | 438 | +0.00059 [-0.00162, +0.00333] | 629 | -0.00090 [-0.00261, +0.00075] | NO_DETECTABLE_INCREMENT |

### Next-session large-move frequencies (Wilson 95% CI)

| Era / VIX regime | Sessions | Median range | range≥100 | range≥200 | range≥350 | range≥500 |
|---|---|---|---|---|---|---|
| 2008-2015 | vix<15 | 459 | 36.5 | 0.0131 [0.006, 0.0282] | 0.0 [0, 0.0083] | 0.0 [0, 0.0083] | 0.0 [0, 0.0083] |
| 2008-2015 | 15<=vix<=25 | 919 | 37.5 | 0.0381 [0.0275, 0.0525] | 0.0022 [0.0006, 0.0079] | 0.0 [0, 0.0042] | 0.0 [0, 0.0042] |
| 2008-2015 | vix>25 | 445 | 47.8 | 0.0809 [0.059, 0.11] | 0.0045 [0.0012, 0.0162] | 0.0 [0, 0.0086] | 0.0 [0, 0.0086] |
| 2016-2023 | vix<15 | 649 | 66.0 | 0.265 [0.2325, 0.3003] | 0.0709 [0.0536, 0.0933] | 0.0092 [0.0042, 0.02] | 0.0 [0, 0.0059] |
| 2016-2023 | 15<=vix<=25 | 817 | 189.8 | 0.8482 [0.822, 0.8712] | 0.459 [0.4251, 0.4933] | 0.1065 [0.0871, 0.1295] | 0.0196 [0.0121, 0.0316] |
| 2016-2023 | vix>25 | 289 | 328.0 | 0.9827 [0.9601, 0.9926] | 0.8374 [0.7904, 0.8754] | 0.4325 [0.3767, 0.4902] | 0.1765 [0.1368, 0.2246] |
| 2024-2026 | vix<15 | 159 | 245.8 | 0.9937 [0.9652, 0.9989] | 0.717 [0.6425, 0.7812] | 0.239 [0.1794, 0.3109] | 0.0818 [0.0484, 0.1349] |
| 2024-2026 | 15<=vix<=25 | 435 | 395.0 | 1.0 [0.9912, 1.0] | 0.9218 [0.8928, 0.9435] | 0.5931 [0.5463, 0.6383] | 0.3241 [0.2819, 0.3695] |
| 2024-2026 | vix>25 | 35 | 650.2 | 1.0 [0.9011, 1] | 1.0 [0.9011, 1] | 0.8571 [0.7062, 0.9374] | 0.6571 [0.4915, 0.7917] |

### NQ target-before-stop (hourly, 544 sessions, holdout from 2025-11-21)

Entry at the 15:00 UTC hourly open; same-bar touches resolved with 1m/5m bars when available, otherwise STOP_FIRST. Net = 0.75 points round-trip cost.

| Horizon | Target/Stop | Side | Dev n | Dev target-first | Dev EV [CI] | Hold n | Hold target-first | Hold EV [CI] | Ambiguous→stop | Status |
|---|---|---|---|---|---|---|---|---|---|---|
| 6h | 100/100 | LONG | 324 | 0.3765 | -2.208 [-12.105, 7.689] | 217 | 0.47 | 3.816 [-8.95, 16.581] | 10 | REJECTED |
| 6h | 100/100 | SHORT | 324 | 0.392 | -2.378 [-12.275, 7.519] | 217 | 0.4101 | -9.924 [-22.645, 2.797] | 10 | REJECTED |
| 6h | 200/100 | LONG | 324 | 0.0957 | -4.131 [-15.707, 7.445] | 217 | 0.212 | 11.309 [-5.195, 27.813] | 1 | REJECTED |
| 6h | 200/100 | SHORT | 324 | 0.179 | -2.148 [-14.641, 10.344] | 217 | 0.2074 | -2.594 [-19.041, 13.852] | 3 | REJECTED |
| 6h | 200/200 | LONG | 324 | 0.1204 | -3.292 [-17.865, 11.282] | 217 | 0.2627 | 9.724 [-10.868, 30.315] | 0 | REJECTED |
| 6h | 200/200 | SHORT | 324 | 0.213 | 1.792 [-12.782, 16.365] | 217 | 0.2396 | -11.224 [-31.815, 9.368] | 0 | REJECTED |
| 6h | 350/175 | LONG | 324 | 0.0278 | -5.671 [-20.498, 9.156] | 217 | 0.0461 | -1.342 [-22.334, 19.65] | 1 | REJECTED |
| 6h | 350/175 | SHORT | 324 | 0.0772 | 3.52 [-12.582, 19.622] | 217 | 0.106 | -3.855 [-26.588, 18.879] | 0 | REJECTED |
| 6h | 500/250 | LONG | 324 | 0.0123 | -7.546 [-24.01, 8.918] | 217 | 0.0138 | 0.016 [-22.561, 22.594] | 0 | REJECTED |
| 6h | 500/250 | SHORT | 324 | 0.0247 | 3.215 [-14.012, 20.442] | 217 | 0.0369 | -4.081 [-29.339, 21.178] | 0 | REJECTED |
| 24h | 100/100 | LONG | 326 | 0.4724 | -4.249 [-15.033, 6.535] | 217 | 0.5253 | 4.877 [-8.409, 18.162] | 10 | REJECTED |
| 24h | 100/100 | SHORT | 326 | 0.4939 | -0.318 [-11.109, 10.473] | 217 | 0.447 | -10.985 [-24.222, 2.251] | 10 | REJECTED |
| 24h | 200/100 | LONG | 326 | 0.2546 | -3.473 [-17.773, 10.827] | 217 | 0.3641 | 10.516 [-8.658, 29.691] | 2 | REJECTED |
| 24h | 200/100 | SHORT | 326 | 0.2822 | -3.992 [-18.533, 10.55] | 217 | 0.3272 | 2.331 [-16.372, 21.034] | 3 | REJECTED |
| 24h | 200/200 | LONG | 326 | 0.3313 | 3.16 [-15.757, 22.076] | 217 | 0.4608 | -2.567 [-28.408, 23.274] | 0 | REJECTED |
| 24h | 200/200 | SHORT | 326 | 0.3681 | -4.66 [-23.576, 14.257] | 217 | 0.4654 | 1.067 [-24.774, 26.908] | 0 | REJECTED |
| 24h | 350/175 | LONG | 326 | 0.1135 | -3.787 [-24.105, 16.531] | 217 | 0.1751 | -24.051 [-52.241, 4.14] | 1 | REJECTED |
| 24h | 350/175 | SHORT | 326 | 0.184 | -4.012 [-26.188, 18.165] | 217 | 0.2811 | 8.077 [-23.01, 39.164] | 0 | REJECTED |
| 24h | 500/250 | LONG | 326 | 0.0368 | -3.653 [-27.503, 20.198] | 217 | 0.0876 | -9.291 [-45.244, 26.661] | 0 | REJECTED |
| 24h | 500/250 | SHORT | 326 | 0.1074 | -0.782 [-26.666, 25.101] | 217 | 0.1889 | 23.865 [-15.248, 62.978] | 0 | REJECTED |
## ES

Sessions 2000-09-18 → 2026-11-05: 6061 usable after excluding 462 near 66 Databento volume rolls.

| Task | Config | Dev n | Dev Brier model | Dev Brier baseline | Dev Δ [95% CI] | Dev AUC | Holdout Δ | Holdout AUC | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| direction_next_settle_up | price_logit | 3582 | 0.25207 | 0.24874 | +0.00332 [+0.00138, +0.00551] | 0.4943 | +0.00448 | 0.4918 | REJECT |
| direction_next_settle_up | all_logit | 3025 | 0.25391 | 0.24898 | +0.00493 [+0.00267, +0.00745] | 0.4869 | +0.00124 | 0.4956 | REJECT |
| direction_next_settle_up | all_lgbm | 3025 | 0.25151 | 0.24898 | +0.00253 [+0.00066, +0.00444] | 0.4971 | +0.00147 | 0.5055 | REJECT |
| direction_next_settle_up | price+volatility_logit | 3582 | 0.25283 | 0.24874 | +0.00409 [+0.00170, +0.00670] | 0.4967 | +0.00206 | 0.4949 | REJECT |
| direction_next_settle_up | price+rates_credit_logit | 3079 | 0.25270 | 0.24881 | +0.00389 [+0.00196, +0.00608] | 0.4973 | +0.00630 | 0.4861 | REJECT |
| direction_next_settle_up | price+positioning_logit | 3025 | 0.25504 | 0.24898 | +0.00606 [+0.00306, +0.00934] | 0.4927 | +0.00388 | 0.5034 | REJECT |
| direction_next_settle_up | price+filings_logit | 3582 | 0.25186 | 0.24874 | +0.00312 [+0.00128, +0.00509] | 0.4944 | +0.00428 | 0.4920 | REJECT |
| compression_next_range_lt_0.6atr | price_logit | 3582 | 0.13509 | 0.13690 | -0.00181 [-0.01046, +0.00770] | 0.7369 | -0.02016 | 0.7924 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | all_logit | 3025 | 0.14404 | 0.13651 | +0.00753 [-0.00416, +0.02121] | 0.7344 | -0.02141 | 0.8108 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | all_lgbm | 3025 | 0.12504 | 0.13651 | -0.01148 [-0.01816, -0.00412] | 0.7562 | -0.01939 | 0.7811 | ACCEPT_RESEARCH_ONLY |
| compression_next_range_lt_0.6atr | price+volatility_logit | 3582 | 0.13691 | 0.13690 | +0.00002 [-0.00930, +0.01069] | 0.7487 | -0.02462 | 0.8145 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | price+rates_credit_logit | 3079 | 0.14398 | 0.13698 | +0.00700 [-0.00405, +0.02018] | 0.7344 | -0.02105 | 0.7918 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | price+positioning_logit | 3025 | 0.14173 | 0.13651 | +0.00522 [-0.00497, +0.01644] | 0.7349 | -0.02074 | 0.7866 | INCONCLUSIVE |
| compression_next_range_lt_0.6atr | price+filings_logit | 3582 | 0.13468 | 0.13690 | -0.00221 [-0.01079, +0.00720] | 0.7372 | -0.01966 | 0.7905 | INCONCLUSIVE |
| range_ge_25pts | price_logit | 3582 | 0.12633 | 0.17703 | -0.05071 [-0.06665, -0.03626] | 0.8939 | -0.00057 | 0.8679 | ACCEPT_RESEARCH_ONLY |
| range_ge_25pts | all_logit | 3025 | 0.12390 | 0.16427 | -0.04037 [-0.05906, -0.02402] | 0.8983 | -0.00062 | 0.8829 | ACCEPT_RESEARCH_ONLY |
| range_ge_25pts | all_lgbm | 3025 | 0.12985 | 0.16427 | -0.03441 [-0.04997, -0.02054] | 0.8881 | -0.00095 | 0.8989 | ACCEPT_RESEARCH_ONLY |
| range_ge_25pts | price+volatility_logit | 3582 | 0.12458 | 0.17703 | -0.05245 [-0.06892, -0.03780] | 0.8964 | -0.00068 | 0.9011 | ACCEPT_RESEARCH_ONLY |
| range_ge_25pts | price+rates_credit_logit | 3079 | 0.12407 | 0.16477 | -0.04070 [-0.05894, -0.02545] | 0.8970 | -0.00067 | 0.8924 | ACCEPT_RESEARCH_ONLY |
| range_ge_25pts | price+positioning_logit | 3025 | 0.12423 | 0.16427 | -0.04003 [-0.05906, -0.02325] | 0.8978 | -0.00055 | 0.8632 | ACCEPT_RESEARCH_ONLY |
| range_ge_25pts | price+filings_logit | 3582 | 0.12615 | 0.17703 | -0.05088 [-0.06698, -0.03628] | 0.8942 | -0.00057 | 0.8679 | ACCEPT_RESEARCH_ONLY |
| range_ge_50pts | price_logit | 3362 | 0.08876 | 0.11727 | -0.02850 [-0.04335, -0.01552] | 0.8554 | -0.03183 | 0.7809 | ACCEPT_RESEARCH_ONLY |
| range_ge_50pts | all_logit | 2805 | 0.09656 | 0.12252 | -0.02596 [-0.04196, -0.01073] | 0.8561 | -0.03793 | 0.8012 | ACCEPT_RESEARCH_ONLY |
| range_ge_50pts | all_lgbm | 2805 | 0.09909 | 0.12252 | -0.02343 [-0.03684, -0.01202] | 0.8594 | -0.03570 | 0.8077 | ACCEPT_RESEARCH_ONLY |
| range_ge_50pts | price+volatility_logit | 3362 | 0.09440 | 0.11727 | -0.02287 [-0.03667, -0.01111] | 0.8372 | -0.03431 | 0.7917 | ACCEPT_RESEARCH_ONLY |
| range_ge_50pts | price+rates_credit_logit | 2859 | 0.09396 | 0.12115 | -0.02719 [-0.04099, -0.01477] | 0.8570 | -0.03258 | 0.7854 | ACCEPT_RESEARCH_ONLY |
| range_ge_50pts | price+positioning_logit | 2805 | 0.09613 | 0.12252 | -0.02640 [-0.04186, -0.01286] | 0.8553 | -0.03285 | 0.7883 | ACCEPT_RESEARCH_ONLY |
| range_ge_50pts | price+filings_logit | 3362 | 0.09547 | 0.11727 | -0.02180 [-0.03518, -0.01025] | 0.8356 | -0.03186 | 0.7814 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | price_logit | 1974 | 0.05300 | 0.06613 | -0.01312 [-0.02767, -0.00226] | 0.8323 | -0.03591 | 0.7908 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | all_logit | 1945 | 0.05796 | 0.06710 | -0.00914 [-0.01762, -0.00181] | 0.7921 | -0.03290 | 0.7887 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | all_lgbm | 1945 | 0.06392 | 0.06710 | -0.00318 [-0.00940, +0.00290] | 0.7542 | -0.02538 | 0.7644 | INCONCLUSIVE |
| range_ge_100pts | price+volatility_logit | 1974 | 0.05320 | 0.06613 | -0.01293 [-0.02758, -0.00162] | 0.8344 | -0.03828 | 0.7943 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | price+rates_credit_logit | 1974 | 0.05545 | 0.06613 | -0.01068 [-0.02459, +0.00041] | 0.8200 | -0.03504 | 0.7852 | INCONCLUSIVE |
| range_ge_100pts | price+positioning_logit | 1945 | 0.05404 | 0.06710 | -0.01307 [-0.02539, -0.00300] | 0.8216 | -0.03224 | 0.7860 | ACCEPT_RESEARCH_ONLY |
| range_ge_100pts | price+filings_logit | 1974 | 0.05508 | 0.06613 | -0.01105 [-0.02621, +0.00055] | 0.8272 | -0.03573 | 0.7905 | INCONCLUSIVE |
| range_ge_150pts | price_logit | 879 | 0.03811 | 0.03750 | +0.00061 [-0.00412, +0.00551] | 0.4355 | -0.00563 | 0.7488 | INCONCLUSIVE |
| range_ge_150pts | all_logit | 879 | 0.03759 | 0.03750 | +0.00008 [-0.00316, +0.00302] | 0.3918 | -0.00112 | 0.8496 | INCONCLUSIVE |
| range_ge_150pts | all_lgbm | 879 | 0.03903 | 0.03750 | +0.00153 [-0.00006, +0.00332] | 0.2237 | -0.00479 | 0.6864 | INCONCLUSIVE |
| range_ge_150pts | price+volatility_logit | 879 | 0.03695 | 0.03750 | -0.00056 [-0.00386, +0.00242] | 0.4055 | -0.00729 | 0.7497 | INCONCLUSIVE |
| range_ge_150pts | price+rates_credit_logit | 879 | 0.03897 | 0.03750 | +0.00146 [-0.00506, +0.00810] | 0.4072 | -0.00590 | 0.8413 | INCONCLUSIVE |
| range_ge_150pts | price+positioning_logit | 879 | 0.03788 | 0.03750 | +0.00038 [-0.00370, +0.00444] | 0.4155 | -0.00470 | 0.7458 | INCONCLUSIVE |
| range_ge_150pts | price+filings_logit | 879 | 0.03987 | 0.03750 | +0.00237 [-0.00366, +0.00892] | 0.4236 | -0.00506 | 0.7506 | INCONCLUSIVE |

### Feature-family increment over price-only logistic (Brier Δ, matched sessions; negative = family helps)

| Task | Config | Dev n | Dev Δ [95% CI] | Holdout n | Holdout Δ [95% CI] | Verdict |
|---|---|---|---|---|---|---|
| direction_next_settle_up | all_logit | 3025 | +0.00106 [-0.00051, +0.00265] | 580 | -0.00376 [-0.00872, +0.00026] | NO_DETECTABLE_INCREMENT |
| direction_next_settle_up | all_lgbm | 3025 | -0.00134 [-0.00293, +0.00016] | 580 | -0.00353 [-0.01131, +0.00244] | NO_DETECTABLE_INCREMENT |
| direction_next_settle_up | price+volatility_logit | 3582 | +0.00076 [+0.00003, +0.00150] | 629 | -0.00242 [-0.00638, +0.00064] | FAMILY_HURTS |
| direction_next_settle_up | price+rates_credit_logit | 3079 | -0.00003 [-0.00112, +0.00104] | 629 | +0.00182 [-0.00117, +0.00501] | NO_DETECTABLE_INCREMENT |
| direction_next_settle_up | price+positioning_logit | 3025 | +0.00219 [+0.00082, +0.00371] | 580 | -0.00112 [-0.00228, -0.00006] | FAMILY_HURTS |
| direction_next_settle_up | price+filings_logit | 3582 | -0.00020 [-0.00083, +0.00039] | 629 | -0.00020 [-0.00066, +0.00018] | NO_DETECTABLE_INCREMENT |
| compression_next_range_lt_0.6atr | all_logit | 3025 | +0.01161 [+0.00654, +0.01737] | 580 | -0.00454 [-0.01112, +0.00302] | FAMILY_HURTS |
| compression_next_range_lt_0.6atr | all_lgbm | 3025 | -0.00740 [-0.01575, +0.00071] | 580 | -0.00251 [-0.01051, +0.00459] | NO_DETECTABLE_INCREMENT |
| compression_next_range_lt_0.6atr | price+volatility_logit | 3582 | +0.00182 [-0.00306, +0.00666] | 629 | -0.00447 [-0.00767, -0.00104] | NO_DETECTABLE_INCREMENT |
| compression_next_range_lt_0.6atr | price+rates_credit_logit | 3079 | +0.01066 [+0.00707, +0.01490] | 629 | -0.00089 [-0.00487, +0.00307] | FAMILY_HURTS |
| compression_next_range_lt_0.6atr | price+positioning_logit | 3025 | +0.00930 [+0.00552, +0.01367] | 580 | -0.00387 [-0.00763, -0.00015] | FAMILY_HURTS |
| compression_next_range_lt_0.6atr | price+filings_logit | 3582 | -0.00041 [-0.00132, +0.00052] | 629 | +0.00049 [-0.00038, +0.00143] | NO_DETECTABLE_INCREMENT |
| range_ge_25pts | all_logit | 3025 | +0.00909 [+0.00236, +0.01641] | 580 | -0.00005 [-0.00018, +0.00010] | FAMILY_HURTS |
| range_ge_25pts | all_lgbm | 3025 | +0.01504 [+0.00801, +0.02243] | 580 | -0.00038 [-0.00117, +0.00021] | FAMILY_HURTS |
| range_ge_25pts | price+volatility_logit | 3582 | -0.00175 [-0.00414, +0.00050] | 629 | -0.00011 [-0.00025, +0.00004] | NO_DETECTABLE_INCREMENT |
| range_ge_25pts | price+rates_credit_logit | 3079 | +0.00775 [+0.00374, +0.01226] | 629 | -0.00010 [-0.00020, -0.00003] | FAMILY_HURTS |
| range_ge_25pts | price+positioning_logit | 3025 | +0.00942 [+0.00309, +0.01622] | 580 | +0.00002 [-0.00006, +0.00009] | FAMILY_HURTS |
| range_ge_25pts | price+filings_logit | 3582 | -0.00018 [-0.00053, +0.00017] | 629 | +0.00000 [-0.00000, +0.00001] | NO_DETECTABLE_INCREMENT |
| range_ge_50pts | all_logit | 2805 | +0.00115 [-0.00257, +0.00751] | 580 | -0.00577 [-0.00858, -0.00305] | NO_DETECTABLE_INCREMENT |
| range_ge_50pts | all_lgbm | 2805 | +0.00368 [-0.00160, +0.00983] | 580 | -0.00355 [-0.01044, +0.00338] | NO_DETECTABLE_INCREMENT |
| range_ge_50pts | price+volatility_logit | 3362 | +0.00563 [-0.00077, +0.01707] | 629 | -0.00247 [-0.00399, -0.00069] | NO_DETECTABLE_INCREMENT |
| range_ge_50pts | price+rates_credit_logit | 2859 | -0.00032 [-0.00195, +0.00129] | 629 | -0.00075 [-0.00268, +0.00116] | NO_DETECTABLE_INCREMENT |
| range_ge_50pts | price+positioning_logit | 2805 | +0.00072 [-0.00120, +0.00388] | 580 | -0.00070 [-0.00187, +0.00045] | NO_DETECTABLE_INCREMENT |
| range_ge_50pts | price+filings_logit | 3362 | +0.00670 [+0.00034, +0.01829] | 629 | -0.00003 [-0.00024, +0.00018] | FAMILY_HURTS |
| range_ge_100pts | all_logit | 1945 | +0.00417 [-0.00241, +0.01377] | 580 | -0.00065 [-0.00438, +0.00273] | NO_DETECTABLE_INCREMENT |
| range_ge_100pts | all_lgbm | 1945 | +0.01012 [+0.00227, +0.02055] | 580 | +0.00687 [-0.00410, +0.01881] | FAMILY_HURTS |
| range_ge_100pts | price+volatility_logit | 1974 | +0.00019 [-0.00141, +0.00242] | 629 | -0.00237 [-0.00646, +0.00127] | NO_DETECTABLE_INCREMENT |
| range_ge_100pts | price+rates_credit_logit | 1974 | +0.00244 [+0.00052, +0.00508] | 629 | +0.00087 [-0.00188, +0.00395] | FAMILY_HURTS |
| range_ge_100pts | price+positioning_logit | 1945 | +0.00024 [-0.00245, +0.00273] | 580 | +0.00002 [-0.00144, +0.00152] | NO_DETECTABLE_INCREMENT |
| range_ge_100pts | price+filings_logit | 1974 | +0.00207 [-0.00041, +0.00535] | 629 | +0.00018 [-0.00167, +0.00206] | NO_DETECTABLE_INCREMENT |
| range_ge_150pts | all_logit | 879 | -0.00052 [-0.00364, +0.00169] | 580 | +0.00335 [-0.00338, +0.01140] | NO_DETECTABLE_INCREMENT |
| range_ge_150pts | all_lgbm | 879 | +0.00092 [-0.00339, +0.00553] | 580 | -0.00032 [-0.00611, +0.00665] | NO_DETECTABLE_INCREMENT |
| range_ge_150pts | price+volatility_logit | 879 | -0.00116 [-0.00366, +0.00065] | 629 | -0.00166 [-0.00426, +0.00077] | NO_DETECTABLE_INCREMENT |
| range_ge_150pts | price+rates_credit_logit | 879 | +0.00086 [-0.00105, +0.00280] | 629 | -0.00027 [-0.00458, +0.00437] | NO_DETECTABLE_INCREMENT |
| range_ge_150pts | price+positioning_logit | 879 | -0.00023 [-0.00119, +0.00061] | 580 | -0.00023 [-0.00124, +0.00058] | NO_DETECTABLE_INCREMENT |
| range_ge_150pts | price+filings_logit | 879 | +0.00176 [+0.00004, +0.00400] | 629 | +0.00056 [-0.00009, +0.00137] | FAMILY_HURTS |

### Next-session large-move frequencies (Wilson 95% CI)

| Era / VIX regime | Sessions | Median range | range≥25 | range≥50 | range≥100 | range≥150 |
|---|---|---|---|---|---|---|
| 2008-2015 | vix<15 | 459 | 15.0 | 0.1285 [0.101, 0.1623] | 0.0022 [0.0004, 0.0122] | 0.0 [0, 0.0083] | 0.0 [0, 0.0083] |
| 2008-2015 | 15<=vix<=25 | 923 | 18.5 | 0.2557 [0.2286, 0.2848] | 0.0217 [0.0141, 0.0332] | 0.0022 [0.0006, 0.0079] | 0.0 [0, 0.0041] |
| 2008-2015 | vix>25 | 445 | 28.2 | 0.591 [0.5447, 0.6357] | 0.1416 [0.1122, 0.177] | 0.0135 [0.0062, 0.0291] | 0.0 [0, 0.0086] |
| 2016-2023 | vix<15 | 650 | 19.5 | 0.3169 [0.2823, 0.3537] | 0.0492 [0.0351, 0.0687] | 0.0015 [0.0003, 0.0087] | 0.0 [0, 0.0059] |
| 2016-2023 | 15<=vix<=25 | 816 | 45.8 | 0.8676 [0.8427, 0.8892] | 0.4314 [0.3978, 0.4656] | 0.0515 [0.0383, 0.0688] | 0.0061 [0.0026, 0.0143] |
| 2016-2023 | vix>25 | 289 | 85.5 | 1.0 [0.9869, 1] | 0.872 [0.8285, 0.9057] | 0.3529 [0.3001, 0.4096] | 0.1073 [0.0766, 0.1482] |
| 2024-2026 | vix<15 | 159 | 48.8 | 0.9245 [0.8727, 0.9563] | 0.4717 [0.3957, 0.549] | 0.0566 [0.0301, 0.1041] | 0.0063 [0.0011, 0.0348] |
| 2024-2026 | 15<=vix<=25 | 435 | 75.2 | 1.0 [0.9912, 1.0] | 0.8161 [0.777, 0.8497] | 0.2575 [0.2186, 0.3006] | 0.0621 [0.043, 0.0888] |
| 2024-2026 | vix>25 | 35 | 140.8 | 1.0 [0.9011, 1] | 1.0 [0.9011, 1] | 0.6857 [0.5202, 0.8145] | 0.4571 [0.3047, 0.6181] |
