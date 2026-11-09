# Phase 3S — bounded futures-data activation decision

**USER_ACTION_REQUIRED. Zero genuine licensed receipts. Price unknown, not zero.**

Phase 3T rechecked process/user/machine credential presence on November 8: absent;
`reports/phase3t_external_access.json`. No paid consumption or new receipt. Load a
key from an operator-protected private file into the current process without
printing it or putting its value in shell history, for example:

```powershell
$env:DATABENTO_API_KEY = [IO.File]::ReadAllText('<approved-private-key-file>').Trim()
python scripts/phase3n_futures.py --research-check
```

Review file/service-account ACLs first. Never put the key itself in chat, Git,
arguments, reports or a command literal. This command is metadata preflight, not
download approval. Actual dataset access, credits and price must come from the
account/provider; no supplied credential or free-credit assumption is authorization
to consume data. The existing exact-quote approval checklist below still applies.
Reuse the exact instructions and existing preflight/quote/approval/reservation system
in `PHASE3P_DATA_ACCESS.md`; do not create a second acquisition mechanism.

## Initial useful scope

Dataset **GLBX.MDP3** (CME Globex), raw **NQZ6 and ESZ6 separately**, input type
`raw_symbol`. Provider resolution must establish actual instrument IDs, tick sizes,
availability, calendar/grid and contract identity; symbols alone prove none of this.
Do not substitute continuous symbols, cash NDX/SPX or ETFs.

Minimum plumbing interval: **2026-11-01 23:00 UTC through exclusive 2026-11-02
22:00 UTC**, one session, `ohlcv-1m`. Maximum 2,760 planned minute slots is neither
an actual receipt count nor a billable quote. This is a plumbing pilot, not adequate
historical coverage for statistical validation. Do not enlarge it automatically.

- **1-minute bars:** existing bounded ingestion validator/receipt path. Require a
  current exact quote and explicit approval before consumption.
- **5-minute bars:** derive aligned five-minute OHLCV from validated complete raw
  one-minute contract bars with constituent provenance; flag partial intervals.
  This is bar aggregation, not manufactured trades/order flow. No separate provider
  `ohlcv-5m` schema is assumed or currently offered by the integration.
- **Trade events (`trades`):** separately quote only the same bounded contracts and
  period after entitlement/schema verification. Event-time/receive-time, prices,
  sizes, flags, sequence/quality and side semantics require genuine records. These
  support volume-at-price only when coverage and provider semantics are verified.
  Current ingest is OHLCV-first: event schemas are not claimed ingestion-ready.
- **Quotes (`tbbo` or `mbp-1`):** optional separate quote/approval, justified by
  spread/slippage and trade-context diagnostics. Verify historical schema contents;
  do not assume a trade-side flag is genuine aggressor direction without evidence.
- **Depth (`mbp-10` or `mbo`):** defer unless licensed, actually available and
  justified by a written depth-research question. Require separate cost/size
  approval and validated book reconstruction/sequence handling. No DOM/CVD/depth
  may be reconstructed from OHLCV or invented for missing events.

Existing metadata preflight inventories `ohlcv-1m`, `trades`, `tbbo`, `mbp-1`,
`mbp-10`, `mbo`; listing schemas does not establish entitlement or a working event
ingestor. Approve/validate the minimum OHLCV pilot before extending ingestion to
event schemas. Quotes expire; do not reuse old approvals or clear consumption
reservations to force a retry. Only pilot receipts enable subsequent integration.

## Exact user action

Configure `DATABENTO_API_KEY` in an approved private local secret mechanism, not
chat/Git/command history. Confirm CME/GLBX.MDP3 historical access and credits in the
provider account. Run `python scripts/phase3n_futures.py --research-check` for
existing metadata-only checks. The reviewed report must contain actual raw-ID
resolution, availability/count/size and exact provider USD cost for each scope.

Explicit approval must identify that exact request digest, dataset/schema, raw
contract(s), inclusive start/exclusive end, maximum USD/bytes/rows, approved quote
identity/expiry and intended local licensed-storage use. Only then use the existing
bounded pilot CLI documented in `PHASE3P_DATA_ACCESS.md`. No approval for event
data, additional contracts/dates or account purchases is implied by OHLCV approval.

After authentic receipts pass validation, use the existing research chain:
contract/session validation → auction/VWAP/ORB features → signals → realistic-cost
backtests → chronological purged/embargoed evaluation → separate calibration and
untouched independent observations. Target-first/stop-first paths require genuine
adequate granularity, tie/ambiguity policy and realistic costs. A single session
cannot calibrate 200–500-point destinations or promote any futures model. All
unsupported probabilities remain null and new candidates remain NO_PROMOTION /
NO_TRADE. Missing licensed data remains BLOCKED throughout.
