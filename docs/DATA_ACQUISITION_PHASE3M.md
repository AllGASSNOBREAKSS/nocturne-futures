# Phase 3M data-access decision

**External dependency, not an adapter rewrite.** Rechecked process, Windows user
and machine credentials: Databento, FRED, BLS and Nasdaq Data Link keys absent.
No paid request, subscription or purchase was made. No authentic raw-contract
receipt exists locally; the orchestrated NQ/ES strategy job is data-blocked.

## One actionable acquisition plan

1. Operator obtains authorized **Databento GLBX.MDP3 / CME Globex** historical
   access, exchange license and a provider size/cost quote for the exact bounds
   below. A key alone does not establish entitlement or approval of billable use.
2. Configure `DATABENTO_API_KEY` locally using an approved secret mechanism;
   never commit it or paste it in chat. Confirm licensing/redistribution terms.
3. After explicit approval of any costs, use the existing bounded adapter:

```powershell
python scripts/phase3e_providers.py databento --contract NQZ6 --instrument NQ --start 2026-11-01T23:00:00Z --end 2026-11-02T22:00:00Z --license-scope approved_private_research
python scripts/phase3e_providers.py databento --contract ESZ6 --instrument ES --start 2026-11-01T23:00:00Z --end 2026-11-02T22:00:00Z --license-scope approved_private_research
```

Dataset `GLBX.MDP3`, schema `ohlcv-1m`, `stype_in=raw_symbol`. Pilot planning
maximum: 2,760 minute rows for two 23-hour sessions; derive complete 5m buckets
only. This is engineering coverage, not a predictive training sample.

4. Verify hashes, raw/export equivalence, tick alignment, actual contract and
   instrument mappings, timezone/DST and session bounds, missing/duplicate bars,
   completeness, provider latency/vintage evidence and overlap revisions.
   Reuse `phase3l_contract_replay.py` and its existing contract-quality gates.
   A bar-end lower bound is not proof of historical publication availability.
5. Expand deliberately across explicit contracts/rolls and regimes; recommend
   3+ years with enough independent events, separate chronological training,
   calibration and untouched evaluation. Calendar years alone do not establish
   statistical adequacy. Do not retune on already-used 2024–2026 history.

## Remaining schemas and price uncertainty

- Tier 1: `ohlcv-1m`, genuine volume, raw symbols; derive 5m without inventing gaps.
- Tier 2: `trades`, `bbo-1s`/`bbo-1m` or `mbp-1`, as entitled. Validate trade-side
  semantics/unknown side and timestamp sequencing before calculating real delta.
- Tier 3: `mbp-10`/`mbo`, as entitled, with book reconstruction and sequence/gap
  validation. No authentic absorption or replenishment from OHLCV.
- VX requires the separately entitled CFE dataset; do not substitute spot VIX.
- Quote **cost is unknown/null**, not free. Authenticated sizing, compression,
  dates, contracts, schemas and account licensing determine the actual amount.
  Tick/depth size cannot be honestly extrapolated from minute-bar counts.
- Existing bar-only planning assumptions: 695,520 minute rows/year for two active
  instruments at 252 x 23-hour sessions, ~104–174 MB CSV; five-minute rows ~21–35 MB.
  Roll overlap, actual sessions and encoding change these estimates.

Nine existing index/ETF/continuous-proxy daily sources are usable immediately as
retrospective context only, with raw/normalized receipt verification. They are
not licensed NQ/ES intraday data, actual historical publication vintages, or
verified PIT macro/consensus/news feeds. Full entitlement details remain in
`FUTURES_DATA_REQUIREMENTS.md`; do not rebuild working provider infrastructure.
