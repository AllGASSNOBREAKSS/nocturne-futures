# Research job snapshot

Generated: 2026-11-08T20:14:04.351732+00:00

States: {'SUCCEEDED': 77, 'BLOCKED': 15}

Trading: NO_TRADE. No automatic promotions.

Daily index diagnostics are not futures strategy P&L or independent validation.

Shadow operations snapshot: **degraded** (as of 2026-11-08T19:47:22.718424+00:00).
Open issues: ['CYCLE_UNHEALTHY', 'FORECAST_AUDIT:291aac9c9d893a888609aafd', 'FORECAST_AUDIT:cd26071237a957cd7a874933', 'OUTCOME_OVERDUE:291aac9c9d893a888609aafd']

- `DATA_VALIDATION` (research): **SUCCEEDED** — `b26102aae53db5802cba4d08`
  ES=F: 6587 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  ^GSPC: 24828 rows, 1927-12-30 through 2026-11-03, index.
  ^NDX: 10353 rows, 1985-10-01 through 2026-11-03, index.
  ^TNX: 16198 rows, 1962-01-02 through 2026-11-03, rate_index.
  ^VIX: 9280 rows, 1990-01-02 through 2026-11-03, volatility_index.
  NQ=F: 6573 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  QQQ: 6956 rows, 1999-03-10 through 2026-11-02, etf.
  SPY: 8498 rows, 1993-01-29 through 2026-11-02, etf.
  TLT: 6105 rows, 2002-07-30 through 2026-11-02, etf.
- `FEATURE_BUILD` (research): **SUCCEEDED** — `6c5abbdc35131e1c28fe4596`
- `HISTORICAL_BACKTEST` (research): **SUCCEEDED** — `0d1c9bdb4d4add7cd173fd7d`
  ^NDX index-only, 2-bp hypothetical cost: n=6036, mean fraction=-0.00016317, profit factor=0.96774; not futures P&L.
- `WALK_FORWARD_VALIDATION` (research): **SUCCEEDED** — `777d85d11d0c796dbb875b1f`
- `MODEL_TRAINING` (research): **SUCCEEDED** — `e7f72a81f7f1c095f207357a`
- `MODEL_EVALUATION` (research): **SUCCEEDED** — `7c6dbabbfd52cf319ff955e9`
  ^NDX p_model: n=750, Brier=0.249911, AUC=0.47136; development diagnostic only.
  ^NDX p_frequency: n=750, Brier=0.249863, AUC=0.51428; development diagnostic only.
- `FEATURE_BUILD` (research): **SUCCEEDED** — `03080fe1019c73164d273ba8`
- `HISTORICAL_BACKTEST` (research): **SUCCEEDED** — `bbe71518fdcebdb4c077a2a8`
  ^GSPC index-only, 2-bp hypothetical cost: n=6036, mean fraction=-0.00032694, profit factor=0.91690; not futures P&L.
- `WALK_FORWARD_VALIDATION` (research): **SUCCEEDED** — `46ea566985c00e43d4dfdd97`
- `MODEL_TRAINING` (research): **SUCCEEDED** — `804c1127316b5d4e5a01d21b`
- `MODEL_EVALUATION` (research): **SUCCEEDED** — `60d102ffabcb24efa44c9104`
  ^GSPC p_model: n=750, Brier=0.248798, AUC=0.54045; development diagnostic only.
  ^GSPC p_frequency: n=750, Brier=0.249196, AUC=0.51428; development diagnostic only.
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `178923b71b51206a027758eb`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `9fc0dba06268963973e58798`
- `DATA_REFRESH` (shadow): **SUCCEEDED** — `f902b82b1419763c5d945caa`
- `SHADOW_FORECAST` (shadow): **SUCCEEDED** — `592ab80aa3949e626aac0802`
- `FORECAST_MATURITY_CHECK` (shadow): **SUCCEEDED** — `5318c48c334be82fd4c50241`
- `FORWARD_EVALUATION` (shadow): **SUCCEEDED** — `3a8cb1d66fb329c388fc1439`
- `MODEL_DRIFT_MONITOR` (shadow): **SUCCEEDED** — `9ef7193035cfc6ace788456f`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `3e3dbad25e7dbb9728e53425`
- `RESEARCH_REPORT` (shadow): **SUCCEEDED** — `59a82ebe742c39853a3b78a5`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `4967b13b0095b114b0ea31aa`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `161e10fdd4496ca2388e7deb`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `ccade6994dcc9d2fdeaeee3e`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `d2025f4de36ec9aceeab0324`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `3d59d32e0f6c6c5fc0f04111`
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `4f2e80103b6c64cb25c7a584`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `3d938c4ca8e790dac1db89bc`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `2efac0d1ca222ecfdb37c556`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `29e911c2748e9866f86929fe`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `e968d75d9df7ae1057ecb261`
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `019bf92dd8af9b5c65d5572e`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `b0058c9022bddf4029604bf7`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `736aa6a756d56d94fa465525`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `ec02e3c5f5d5c0a1fd3d420f`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `fce812b6ab85f184dcb2fdf1`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `b8ed2c62d048c83e2962e465`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `109aad48e4d7146641d811a6`
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `79ee694228a9a0e27fd9d482`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `dcbb622127451d676ff69069`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `0d044a2333694594463f17b1`
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `a9715adfe952f45c39945767`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `HISTORICAL_BACKTEST` (research): **BLOCKED** — `9cb95320b29b8d1e41e80d9a`
  Reason: AUTHENTIC_CONTRACT_HISTORY_REQUIRED
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `6e68682739e5c178414edc26`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `62a2dad055c56bb8b1373f9e`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `22d63e24f60f070e3437b9fb`
- `DATA_VALIDATION` (research): **SUCCEEDED** — `024aa900f07444329fda489f`
  ES=F: 6587 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  ^GSPC: 24828 rows, 1927-12-30 through 2026-11-03, index.
  ^NDX: 10353 rows, 1985-10-01 through 2026-11-03, index.
  ^TNX: 16198 rows, 1962-01-02 through 2026-11-03, rate_index.
  ^VIX: 9280 rows, 1990-01-02 through 2026-11-03, volatility_index.
  NQ=F: 6573 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  QQQ: 6956 rows, 1999-03-10 through 2026-11-02, etf.
  SPY: 8498 rows, 1993-01-29 through 2026-11-02, etf.
  TLT: 6105 rows, 2002-07-30 through 2026-11-02, etf.
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `3a2a170d36efd4085f4bd389`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `ea1293ed7ef07ef7186fd8db`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `e4a8784372f511f43a35fde5`
- `DATA_VALIDATION` (research): **SUCCEEDED** — `47e2eb46448e5dab560e368b`
  ES=F: 6587 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  ^GSPC: 24828 rows, 1927-12-30 through 2026-11-03, index.
  ^NDX: 10353 rows, 1985-10-01 through 2026-11-03, index.
  ^TNX: 16198 rows, 1962-01-02 through 2026-11-03, rate_index.
  ^VIX: 9280 rows, 1990-01-02 through 2026-11-03, volatility_index.
  NQ=F: 6573 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  QQQ: 6956 rows, 1999-03-10 through 2026-11-02, etf.
  SPY: 8498 rows, 1993-01-29 through 2026-11-02, etf.
  TLT: 6105 rows, 2002-07-30 through 2026-11-02, etf.
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `36443c6fac8ea1f67997b3cc`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `23524ff9ab2069ba10ffe061`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `f1cf88f090f26dcc397bf46a`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `75120ceb00ecacb48be3152d`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `50004684de65020cee0033c5`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `c58c59c02f45dbd082349fbc`
- `DATA_REFRESH` (shadow): **SUCCEEDED** — `a00e5bf3ed23fc6b496f7acc`
- `SHADOW_FORECAST` (shadow): **SUCCEEDED** — `cf914682f79d563e4a9d1b3e`
- `FORECAST_MATURITY_CHECK` (shadow): **SUCCEEDED** — `6a46119627fd1d445c394ff6`
- `FORWARD_EVALUATION` (shadow): **SUCCEEDED** — `258bfa92e87427a87e57919d`
- `MODEL_DRIFT_MONITOR` (shadow): **SUCCEEDED** — `532307848a2317c310d70481`
- `RESEARCH_REPORT` (shadow): **SUCCEEDED** — `d41d9341d48c7b020b7d449d`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `565c88d92b1af7f92e7771f9`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `4dbbf411e3fed003ab663915`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `796a8ef6b22dbab3b672af7f`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `04484bfe2212f4ab1c32f797`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `1859f433d6026ab2f9d8701b`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `720713be5e642086ef52b20e`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `db35f2eaa87f6b93b4ca33ad`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `41ffef97ef054d23a33f9a4e`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `abc9143d9ad6d369f321025c`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `aa5c66c257946db72f6af3da`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `efde1cbff64874e8dab58f78`
- `DATA_VALIDATION` (research): **SUCCEEDED** — `4f31fe86fdc2e21dd384815e`
  ES=F: 6587 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  ^GSPC: 24828 rows, 1927-12-30 through 2026-11-03, index.
  ^NDX: 10353 rows, 1985-10-01 through 2026-11-03, index.
  ^TNX: 16198 rows, 1962-01-02 through 2026-11-03, rate_index.
  ^VIX: 9280 rows, 1990-01-02 through 2026-11-03, volatility_index.
  NQ=F: 6573 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  QQQ: 6956 rows, 1999-03-10 through 2026-11-02, etf.
  SPY: 8498 rows, 1993-01-29 through 2026-11-02, etf.
  TLT: 6105 rows, 2002-07-30 through 2026-11-02, etf.
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `b3b17fbbd3ad42d499508276`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `8c8109ab43c582756ee4ff89`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `5fff2119a23e912a6cf4b7e0`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `3cdaafa6db8335544e5700b0`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `5911e5dfb378696fc706a734`
- `DATA_VALIDATION` (research): **SUCCEEDED** — `c537f9a0a1f9569bf271f340`
  ES=F: 6587 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  ^GSPC: 24828 rows, 1927-12-30 through 2026-11-03, index.
  ^NDX: 10353 rows, 1985-10-01 through 2026-11-03, index.
  ^TNX: 16198 rows, 1962-01-02 through 2026-11-03, rate_index.
  ^VIX: 9280 rows, 1990-01-02 through 2026-11-03, volatility_index.
  NQ=F: 6573 rows, 2000-09-18 through 2026-11-04, futures_proxy.
  QQQ: 6956 rows, 1999-03-10 through 2026-11-02, etf.
  SPY: 8498 rows, 1993-01-29 through 2026-11-02, etf.
  TLT: 6105 rows, 2002-07-30 through 2026-11-02, etf.
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `3efc9dfabd4f767be8e77168`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `73c3bb381a941f1c3dda2d54`
- `DATA_REFRESH` (shadow): **SUCCEEDED** — `7cd1831eef7b20d18ffa1825`
  Reason: COMPONENT_COMPLETED_WITH_QUARANTINE
- `SHADOW_FORECAST` (shadow): **SUCCEEDED** — `169fb2adcc2be9f8adef9e04`
  Reason: COMPONENT_COMPLETED_WITH_QUARANTINE
- `FORECAST_MATURITY_CHECK` (shadow): **SUCCEEDED** — `acf64a1af0033e46aeb84767`
  Reason: COMPONENT_COMPLETED_WITH_QUARANTINE
- `FORWARD_EVALUATION` (shadow): **SUCCEEDED** — `99ada9b5f1eacdae0dcb41f8`
- `MODEL_DRIFT_MONITOR` (shadow): **SUCCEEDED** — `077692ad757ec5c2e67328d7`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `312c100a0f1e2ea8017ae18d`
- `RESEARCH_REPORT` (shadow): **SUCCEEDED** — `85717b5f3f369cf088cac99b`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `c9fb40ca8c2e1b545e90ac6f`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `1efeed912b467863bdce4b6d`
- `RESEARCH_REPORT` (research): **SUCCEEDED** — `b07e90400976213d3f4a2b3b`
