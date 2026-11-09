# Phase 3U — free-data walk-forward backtest (^NDX, index-level)

Generated 2026-11-09T02:21:18.517260+00:00. Fingerprint `de358f794e96e44b`.
Scope: Nasdaq-100 cash index research forecasts. **Not NQ futures, not order flow, not executable P&L.**
Sample: 4624 test sessions, 2008-01-02 to 2026-11-02; annual expanding refits, 5-day embargo.

**Verdicts:** direction `INCONCLUSIVE`, range `FAIL`. NO_PROMOTION / NO_TRADE.

## Direction (next session close > open)

| Era | Model | n | AUC | Bal. acc | Brier | Log loss |
|---|---|---|---|---|---|---|
| development | frequency | 3969 | 0.4959 | 0.5000 | 0.24852 | 0.69018 |
| development | base logistic | 3969 | 0.4896 | 0.4948 | 0.25081 | 0.69498 |
| development | free-data logistic | 3969 | 0.4838 | 0.4917 | 0.25144 | 0.69622 |
| exposed | frequency | 655 | 0.4898 | 0.5000 | 0.24884 | 0.69082 |
| exposed | base logistic | 655 | 0.5059 | 0.4991 | 0.25088 | 0.69498 |
| exposed | free-data logistic | 655 | 0.5061 | 0.5004 | 0.25120 | 0.69574 |
| all | frequency | 4624 | 0.4920 | 0.5000 | 0.24856 | 0.69027 |
| all | base logistic | 4624 | 0.4894 | 0.4950 | 0.25082 | 0.69498 |
| all | free-data logistic | 4624 | 0.4856 | 0.4924 | 0.25141 | 0.69615 |

Brier differences (negative = first model better), 95% monthly block-bootstrap CI:

- development `brier_free_minus_frequency`: +0.002927 [+0.001360, +0.004448]
- development `brier_free_minus_base`: +0.000629 [-0.000762, +0.001961]
- development `brier_base_minus_frequency`: +0.002298 [+0.000768, +0.003925]
- development `pinball_free_minus_trailing`: -0.000517 [-0.000798, -0.000284]
- development `pinball_free_minus_base`: +0.000314 [+0.000049, +0.000699]
- development `pinball_base_minus_trailing`: -0.000831 [-0.001204, -0.000528]
- exposed `brier_free_minus_frequency`: +0.002368 [-0.000898, +0.006401]
- exposed `brier_free_minus_base`: +0.000318 [-0.002014, +0.002673]
- exposed `brier_base_minus_frequency`: +0.002050 [-0.000469, +0.004862]
- exposed `pinball_free_minus_trailing`: -0.000528 [-0.000990, -0.000208]
- exposed `pinball_free_minus_base`: -0.000124 [-0.000244, -0.000030]
- exposed `pinball_base_minus_trailing`: -0.000403 [-0.000779, -0.000113]

## Next-session range quantiles ((high-low)/close)

| Era | Model | P50 cov | P80 cov | P90 cov | Mean pinball |
|---|---|---|---|---|---|
| development | trailing_baseline | 0.5092 | 0.7944 | 0.8851 | 0.002853 |
| development | base_lgbm | 0.5820 | 0.8224 | 0.9017 | 0.002022 |
| development | free_lgbm | 0.5704 | 0.7999 | 0.8796 | 0.002336 |
| exposed | trailing_baseline | 0.4855 | 0.7863 | 0.8809 | 0.002359 |
| exposed | base_lgbm | 0.5420 | 0.8290 | 0.9069 | 0.001955 |
| exposed | free_lgbm | 0.5420 | 0.8336 | 0.9084 | 0.001831 |
| all | trailing_baseline | 0.5058 | 0.7933 | 0.8845 | 0.002783 |
| all | base_lgbm | 0.5763 | 0.8233 | 0.9025 | 0.002013 |
| all | free_lgbm | 0.5664 | 0.8047 | 0.8837 | 0.002265 |

## Training-window sensitivity (all test years, Brier / AUC)

- `p_base_C0.05_w10`: Brier 0.25015, AUC 0.4936
- `p_base_C0.05_w20`: Brier 0.25145, AUC 0.4882
- `p_base_C0.05_w5`: Brier 0.25042, AUC 0.4950
- `p_base_C0.05_wall`: Brier 0.25081, AUC 0.4899
- `p_base_C0.2_w10`: Brier 0.25018, AUC 0.4935
- `p_base_C0.2_w20`: Brier 0.25144, AUC 0.4876
- `p_base_C0.2_w5`: Brier 0.25044, AUC 0.4948
- `p_base_C0.2_wall`: Brier 0.25082, AUC 0.4894
- `p_base_C1.0_w10`: Brier 0.25018, AUC 0.4935
- `p_base_C1.0_w20`: Brier 0.25143, AUC 0.4875
- `p_base_C1.0_w5`: Brier 0.25044, AUC 0.4947
- `p_base_C1.0_wall`: Brier 0.25083, AUC 0.4894
- `p_free_C0.05_w10`: Brier 0.25107, AUC 0.4866
- `p_free_C0.05_w5`: Brier 0.25111, AUC 0.4960
- `p_free_C0.05_wall`: Brier 0.25117, AUC 0.4886
- `p_free_C0.2_w10`: Brier 0.25131, AUC 0.4839
- `p_free_C0.2_w5`: Brier 0.25141, AUC 0.4948
- `p_free_C0.2_wall`: Brier 0.25141, AUC 0.4856
- `p_free_C1.0_w10`: Brier 0.25142, AUC 0.4833
- `p_free_C1.0_w5`: Brier 0.25158, AUC 0.4950
- `p_free_C1.0_wall`: Brier 0.25152, AUC 0.4850
- `p_frequency`: Brier 0.24856, AUC 0.4920

## Year by year (Brier: frequency / base / free; mean pinball: trailing / base / free)

| Year | n | Brier freq | Brier base | Brier free | AUC free | Pinball trail | Pinball base | Pinball free | Free P80 cov |
|---|---|---|---|---|---|---|---|---|---|
| 2008 | 253 | 0.25004 | 0.25349 | 0.25153 | 0.4887 | 0.006340 | 0.003668 | 0.007863 | 0.4229 |
| 2009 | 252 | 0.24957 | 0.25109 | 0.24995 | 0.4955 | 0.003983 | 0.002182 | 0.003680 | 0.9841 |
| 2010 | 252 | 0.24915 | 0.24845 | 0.24909 | 0.4347 | 0.002495 | 0.002000 | 0.002075 | 0.8571 |
| 2011 | 252 | 0.24942 | 0.25060 | 0.25107 | 0.5063 | 0.002872 | 0.002051 | 0.001973 | 0.8214 |
| 2012 | 250 | 0.24855 | 0.24764 | 0.24791 | 0.5184 | 0.001713 | 0.001400 | 0.001357 | 0.8880 |
| 2013 | 227 | 0.24738 | 0.24496 | 0.24626 | 0.4434 | 0.001320 | 0.001404 | 0.001223 | 0.8634 |
| 2014 | 252 | 0.24772 | 0.24605 | 0.25336 | 0.5022 | 0.001739 | 0.001546 | 0.001441 | 0.8135 |
| 2015 | 252 | 0.24905 | 0.25033 | 0.25006 | 0.5085 | 0.002159 | 0.001808 | 0.001697 | 0.7341 |
| 2016 | 252 | 0.24826 | 0.24851 | 0.24870 | 0.4725 | 0.002174 | 0.001640 | 0.001616 | 0.8690 |
| 2017 | 251 | 0.24557 | 0.24291 | 0.24415 | 0.4943 | 0.001387 | 0.001349 | 0.001336 | 0.9084 |
| 2018 | 251 | 0.25127 | 0.25769 | 0.25903 | 0.5539 | 0.003695 | 0.002360 | 0.002509 | 0.6853 |
| 2019 | 219 | 0.24758 | 0.25264 | 0.25480 | 0.5004 | 0.002039 | 0.001746 | 0.001598 | 0.8493 |
| 2020 | 253 | 0.24584 | 0.24481 | 0.24559 | 0.5088 | 0.005104 | 0.002731 | 0.002572 | 0.7668 |
| 2021 | 252 | 0.24770 | 0.24965 | 0.25047 | 0.4532 | 0.002256 | 0.001680 | 0.001693 | 0.8929 |
| 2022 | 251 | 0.25312 | 0.26750 | 0.26316 | 0.4949 | 0.003864 | 0.003018 | 0.002912 | 0.6534 |
| 2023 | 250 | 0.24579 | 0.25645 | 0.25798 | 0.4783 | 0.002211 | 0.001664 | 0.001589 | 0.8040 |
| 2024 | 252 | 0.24873 | 0.25103 | 0.25488 | 0.4759 | 0.001918 | 0.001724 | 0.001661 | 0.8214 |
| 2025 | 199 | 0.24728 | 0.24952 | 0.24730 | 0.5173 | 0.003235 | 0.002331 | 0.002049 | 0.8291 |
| 2026 | 204 | 0.25048 | 0.25203 | 0.25047 | 0.5237 | 0.002049 | 0.001875 | 0.001828 | 0.8529 |

## Regimes

| Regime | n | AUC free | Brier freq | Brier free | Pinball trail | Pinball free |
|---|---|---|---|---|---|---|
| vix_lt15 | 1405 | 0.4652 | 0.24799 | 0.25230 | 0.001588 | 0.001312 |
| vix_15_25 | 2368 | 0.4970 | 0.24852 | 0.25105 | 0.002331 | 0.001906 |
| vix_gt25 | 851 | 0.4769 | 0.24963 | 0.25094 | 0.006013 | 0.004835 |
| above_200d | 3680 | 0.4873 | 0.24831 | 0.25117 | 0.002188 | 0.001746 |
| below_200d | 944 | 0.4759 | 0.24955 | 0.25233 | 0.005101 | 0.004285 |
| bear_drawdown_gt20pct | 469 | 0.4536 | 0.24954 | 0.25337 | 0.006154 | 0.006254 |

## Hypothetical index exposure (sign of free-model probability, 0.02 dead zone)

Open-to-close index fractions, costs in basis points per trade. **Not NQ P&L; not executable.**

| Era | Rule | Cost | Trades | Win rate | Expectancy | Profit factor | Total return | Max DD |
|---|---|---|---|---|---|---|---|---|
| development | free_primary | 0bps | 3384 | 0.5236 | 0.000007 | 1.0016 | -0.1888 | 0.5364 |
| development | free_primary | 2bps | 3384 | 0.5142 | -0.000193 | 0.9531 | -0.5878 | 0.6427 |
| development | free_primary | 5bps | 3384 | 0.4967 | -0.000493 | 0.8845 | -0.8507 | 0.8535 |
| development | base_primary | 0bps | 3366 | 0.5318 | 0.000002 | 1.0005 | -0.2054 | 0.4727 |
| development | base_primary | 2bps | 3366 | 0.5226 | -0.000198 | 0.9529 | -0.5948 | 0.6033 |
| development | base_primary | 5bps | 3366 | 0.5062 | -0.000498 | 0.8856 | -0.8524 | 0.8552 |
| development | always_long | 0bps | 3969 | 0.5475 | 0.000340 | 1.0871 | 1.9293 | 0.4078 |
| development | always_long | 2bps | 3969 | 0.5367 | 0.000140 | 1.0351 | 0.3245 | 0.4221 |
| development | always_long | 5bps | 3969 | 0.5198 | -0.000160 | 0.9614 | -0.5974 | 0.6730 |
| exposed | free_primary | 0bps | 631 | 0.5388 | 0.000392 | 1.1146 | 0.2363 | 0.1570 |
| exposed | free_primary | 2bps | 631 | 0.5309 | 0.000192 | 1.0547 | 0.0898 | 0.1878 |
| exposed | free_primary | 5bps | 631 | 0.5119 | -0.000108 | 0.9706 | -0.0982 | 0.2505 |
| exposed | base_primary | 0bps | 619 | 0.5283 | 0.000062 | 1.0176 | 0.0050 | 0.1893 |
| exposed | base_primary | 2bps | 619 | 0.5170 | -0.000138 | 0.9617 | -0.1121 | 0.2395 |
| exposed | base_primary | 5bps | 619 | 0.4992 | -0.000438 | 0.8833 | -0.2626 | 0.3305 |
| exposed | always_long | 0bps | 655 | 0.5344 | 0.000321 | 1.0926 | 0.1896 | 0.1590 |
| exposed | always_long | 2bps | 655 | 0.5267 | 0.000121 | 1.0339 | 0.0436 | 0.1900 |
| exposed | always_long | 5bps | 655 | 0.5084 | -0.000179 | 0.9516 | -0.1426 | 0.2538 |

## Point-in-time join audit

- VIXCLS: {'matched_fraction': 1.0, 'median_lag_days': 0.083, 'min_lag_days': 0.0833}
- VXNCLS: {'matched_fraction': 0.9594, 'median_lag_days': 0.083, 'min_lag_days': 0.0833}
- T10Y2Y: {'matched_fraction': 1.0, 'median_lag_days': 0.083, 'min_lag_days': 0.0833}
- DGS10: {'matched_fraction': 1.0, 'median_lag_days': 0.083, 'min_lag_days': 0.0833}
- BAA10Y: {'matched_fraction': 1.0, 'median_lag_days': 0.083, 'min_lag_days': 0.0833}
- WALCL: {'matched_fraction': 0.8896, 'median_lag_days': 4.083, 'min_lag_days': 0.0833}
- DTWEXBGS: {'matched_fraction': 0.7757, 'median_lag_days': 0.083, 'min_lag_days': 0.0833}
- CFTC_209742: {'matched_fraction': 0.7425, 'median_lag_days': 2.125, 'min_lag_days': 0.125}
- CFTC_13874A: {'matched_fraction': 0.7425, 'median_lag_days': 2.125, 'min_lag_days': 0.125}
- SEC_10K_10Q: {'rows': 912, 'rule': 'acceptance time <= cutoff, 5-day count'}

## Limitations

- Cash index, not NQ/ES contracts; no roll, no futures session, no order flow.
- FRED/CFTC values are latest vintages; daily market series are rarely revised, revisable macro series are excluded.
- Conservative availability lags reduce, but cannot prove absence of, publication-time error.
- SEC ticker set is today's megacaps (survivorship-biased membership).
- 2024+ was examined by earlier phases with other features; it is not an untouched holdout.
- Hypothetical index exposure ignores financing, futures basis and realistic execution.
