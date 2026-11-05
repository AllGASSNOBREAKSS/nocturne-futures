# Phase 3P — futures acquisition decision

**Externally BLOCKED; zero licensed NQ/ES rows.** Rechecked process, Windows user
and machine scopes: Databento, FRED, BLS and Nasdaq Data Link keys are absent.
Existing free preflight returned DATA_BLOCKED, cost null, consumption false.
No authenticated entitlement, credit, symbol-ID or size claim is possible.
No provider adapter was rebuilt and no paid request was attempted.

1. Configure `DATABENTO_API_KEY` through a local approved secret mechanism, never
   chat, command history or Git. Operator must verify account license, CME Globex
   access and any actual promotional credits.
2. Run `python scripts/phase3n_futures.py --research-check`. Existing metadata-only
   preflight checks **GLBX.MDP3**, offerings/ranges/conditions, raw IDs and exact
   provider count/size/USD quotes. Offerings alone do not prove entitlement.
3. Minimum plumbing pilot: `ohlcv-1m`, **NQZ6 and ESZ6 separately**, UTC
   `2026-11-01T23:00:00Z` to exclusive `2026-11-02T22:00:00Z`.
   At most 2,760 planned minute slots is neither a provider count nor a price.
   Actual quoted cost remains **unknown**, not zero.
4. Review each saved quote and explicitly authorize its exact scope and USD/byte
   budget, including zero-dollar/credit-consuming requests. Approval JSON fields,
   expiry and reservation safeguards remain as in `PHASE3N_DATA_DECISION.md`.
5. Only after approval, start the existing bounded downloader:

```powershell
python scripts/phase3e_providers.py databento --contract NQZ6 --instrument NQ --start 2026-11-01T23:00:00Z --end 2026-11-02T22:00:00Z --license-scope "<actual-license-reference>" --quote "<saved-NQ-quote.json>" --approval "<authorized-NQ-approval.json>"
```

Repeat separately with ESZ6/ES and its own quote/approval. Then run
`python scripts/phase3n_futures.py --research-check` and the existing research
lane for receipt replay and diagnostics. Preserve all raw/partial evidence and
consumption reservations; never delete them to retry a charged request.

Validate ID, tick, volume, UTC/DST/calendar/grid, availability, roll and complete
5-minute aggregation first. A one-session pilot is not predictive validation.
True volume-at-price/CVD requires separately licensed `trades` with side semantics;
bid/ask requires `tbbo`/`mbp-1`; depth requires `mbp-10`/`mbo` and sequence checks.
Each requires separate quotes, approvals and appropriate ingestion validation.
OHLCV does not supply those inputs. No authentic direction, session, 100/200/350/500
point target-first or survival probability can yet be reported.
