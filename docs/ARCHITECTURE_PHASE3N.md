# Phase 3N — consumption approval and receipt-to-engine boundary

```mermaid
flowchart LR
  M[Free metadata / symbology] --> Q[Request-bound provider quote]
  Q --> A[Explicit fresh operator approval]
  A --> R[Durable consumption reservation]
  R --> B[Bounded archived raw body]
  B --> V[ID / timestamps / tick / volume validation]
  V --> C[Immutable contract receipt]
  C --> E[Existing ORB / bar-VWAP engines]
  E --> D[Diagnostic targets / costs / reports]
  D --> G[NO_PROMOTION / NO_TRADE]
```

New Forq frame: “Nocturne 3N — approve before metered data”; existing elements
were not changed. This flow is implemented on top of the Phase 3M orchestrator,
not as another scheduler or quantitative engine.

- `adapters/databento_access.py`: allowlisted metadata-only preflight, content-
  hashed provider evidence, quoted count/bytes/USD, symbology coverage and
  request-bound approval validation. It never invokes time-series or batch jobs.
- `adapters/databento.py`: existing bar adapter now blocks metered consumption
  without quote/approval; locks/reserves before the request, caps response bytes,
  archives rejected data, validates quoted ID and ticks, and blocks blind retry.
- `research/contract_replay.py`: existing replay also verifies archived approval
  and quote bindings for new guarded receipts. Legacy receipts retain their
  original provenance rather than getting a retroactive authorization label.
- `research/futures_pilot.py`: existing `_signals`, `_run` and target-label builder
  consume verified single-contract receipts. Only complete baseline RTH grids
  qualify. ORB and explicitly labeled bar-VWAP diagnostics include cost sensitivity,
  simulated fills/bar-extreme MFE/MAE bounds, yearly summaries and separate
  ambiguity-aware target labels. One-contract full-TP1 execution avoids fractional
  scale-outs. Explicit cashflow-v2 counts entry/exit slippage once each and charges
  commissions by contract quantity; legacy-v1 remains reproducible, not endorsed.
  Arithmetic tests do not validate real fill behavior or an execution edge.
- `research/jobs.py` extends the existing `HISTORICAL_BACKTEST/raw_futures` handler;
  scheduled research now checks NQ and ES separately. No paid request runs here.
  Empty inventories are BLOCKED, not zero-trade backtest successes. Input hashes
  and code identity retain idempotency across dates and manual/scheduled runs.
  Old index experiments require explicit `--index-diagnostics`; default periodic
  work validates public sources and checks changed futures receipts, not repeated
  models on the same insufficient data.
- `scripts/phase3n_futures.py`: one non-consumption access report and optional
  bounded jobs. Immutable report/evidence history is under ignored private
  `data/licensed/databento_metadata/`; the public latest JSON is a timestamped view.
- `/v1/data/futures-readiness` retains its existing response with an additive
  `acquisition_snapshot`; GET neither probes the provider nor starts a download.

Frozen model/forecast paths, inference scheduling, promotion gates and execution
controls are unchanged. True volume profiles, CVD, depth/sequence analysis, actual
direction/target/survival probabilities and new model training remain gated by
authentic suitable inputs and independent validation. A pilot diagnostic is not
historical PIT certification or statistical strategy validation.
