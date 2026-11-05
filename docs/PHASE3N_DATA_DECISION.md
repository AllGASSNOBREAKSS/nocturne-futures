# Phase 3N — futures acquisition decision

Observed 2026-11-05 UTC. **DATA_BLOCKED; no consumption authorized or attempted.**
Machine evidence: `reports/phase3n_futures_access.json`. This is the current
acquisition decision; prior phase acquisition documents are historical context.

## What was actually verified

- No Databento, FRED, BLS or Nasdaq Data Link key in checked process, Windows user
  or machine scopes. No secret value was read into output.
- All three supplied official URLs returned HTTP 200; bodies, receipt times and
  hashes are archived privately. Fetch success does not establish rendered
  pricing terms, account balance, new-account eligibility or exchange entitlement.
- The [Historical API reference](https://databento.com/docs/api-historical)
  documents free metadata/symbology access, metered time-series consumption,
  repeated charges for duplicate streaming requests, and these interfaces:
  `metadata.list_datasets`, `list_schemas`, `get_dataset_range`,
  `get_dataset_condition`, `get_record_count`, `get_billable_size`, `get_cost`,
  and POST `symbology.resolve`.
- Billing uses uncompressed binary bytes, not saved CSV size. Cost/size estimates
  can be overstated for non-10-minute-aligned bounds. The chosen bounds align.
- The dataset and pricing pages are
  https://databento.com/docs/knowledge-base/datasets/glbx-mdp3 and
  https://databento.com/pricing. **Account credit eligibility is unverified**.
  No advertised credit amount is treated as our available balance or permission.

## Exact bounded pilot, pending authenticated resolution

Dataset `GLBX.MDP3`; schema `ohlcv-1m`; `stype_in=raw_symbol`.
Candidate raw contracts **NQZ6** and **ESZ6**, one request each, from
`2026-11-01T23:00:00Z` through exclusive `2026-11-02T22:00:00Z`.
These are explicit proposed December contracts, **not provider-resolved IDs yet**.
Symbology must cover every UTC date with a single instrument ID; partial, missing
or changing mappings block the pilot. No continuous or back-adjusted substitution.

Planning maximum: 1,380 minute slots per contract, 2,760 total under the 23-hour
assumption. Missing messages are not filled or automatically called outages;
exchange calendar, maintenance and no-trade evidence are separate requirements.
CSV/response bytes are not billable binary bytes. The existing annual bar-only
storage assumptions remain 104–174 MB of minute CSV plus 21–35 MB of derived 5m
CSV for two active instruments; actual rolls/sessions/encoding change that.

**Actual provider record counts, entitled historical range, billable bytes and
USD pilot cost are all null.** Without an authorized key, no account-bound quote
can be produced. Cost is unknown, not zero; fixture costs are not market quotes.

## Operator activation, quote, then separate authorization

1. Sign in to the Databento portal under an authorized account. Verify identity,
   any current promotional eligibility/expiry and available credit, account usage
   limits and the applicable CME historical license/redistribution terms. Do not
   assume a listed dataset or a key grants every schema or free consumption.
2. Configure `DATABENTO_API_KEY` via an approved local secret mechanism, not chat,
   command history, committed files or logs. No subscription is authorized here.
3. Run the **non-consumption** preflight:

```powershell
python scripts/phase3n_futures.py --public-docs --research-check
```

With a key this queries only documented free metadata/symbology. It checks schema
offerings, entitled schema range, available dataset conditions, raw-contract ID
mapping, provider count/size/cost, and archives response-body hashes. Schema
offerings are not independently a grant of access. With no key it makes no
authenticated calls and returns DATA_BLOCKED (exit 1).

4. Review the resulting per-contract quote in
   `data/licensed/databento_metadata/quotes/<quote_id>.json`. Obtain explicit user
   authorization for the exact request, quote and maximum budget **before** any
   metered request, including zero-price or promotional-credit consumption.
5. Only after that authorization, create a local approval JSON containing:
   `quote_id`, `authorized: true`, a non-secret `operator_reference`, UTC
   `approved_at`/`expires_at`, decimal-string `max_cost_usd` and integer
   `max_billable_bytes`. Expiry must be within 24 hours of quote generation.
   The agent does not generate an approved file on the user's behalf.
6. Use the existing adapter, now guarded:

```powershell
python scripts/phase3e_providers.py databento --contract NQZ6 --instrument NQ --start 2026-11-01T23:00:00Z --end 2026-11-02T22:00:00Z --license-scope "<actual-license-reference>" --quote "<saved-NQ-quote.json>" --approval "<authorized-NQ-approval.json>"
```

Repeat separately for ES using its own quote/approval. No automatic paid download
exists in either scheduler. The adapter now intentionally limits acquisition to
one raw NQ/ES contract and at most 24 hours; bulk/daily-chunk loops are not a way
to bypass quote approval. Historical unguarded examples must not be used.

## Cost and integrity controls

- Canonical quote hash binds instrument, contract, schema, date bounds and provider
  responses. Approval must match, be fresh and cover quoted USD/billable bytes.
  These are trusted local operator records and integrity hashes, not provider-
  signed credentials or protection against malicious local filesystem edits.
- This is a **quote-budget check, not a provider-enforced final-invoice ceiling**.
  Actual billing depends on provider delivery. Set/review account-side limits and
  billing terms if a hard monetary ceiling is required before approving use.
- Durable reservation precedes the network, under a per-request OS lock. An
  uncertain/failed consumption attempt cannot automatically be streamed again.
  Reconcile usage with the provider and get explicit new authorization first.
- Successful raw bodies are archived before normalization, including rejected
  bodies. Truncated streams retain bounded prefixes and separate review events.
  HTTP error bodies/auth headers are not copied into reports. Completed local
  receipts can be reused without another request or charge.
- Default decoded-response budget is 16 MiB, configurable up to 64 MiB. This is
  a bounded response buffer, **not** a hard process-RAM or provider-billing cap.
- Verify resolved provider ID, raw symbol where present, ordered/minute-aligned
  exchange timestamps, finite OHLC, 0.25-point instrument tick alignment, integer
  volume, duplicates, range membership and observed count versus quoted count.
  A changed count is a source-review event, not silent tolerance inflation.
- Keep raw response, normalized export, approval object, quote/metadata evidence
  and receipt together. Do not overwrite conflicting evidence or fill gaps.
- Run the existing receipt replay and orchestrated pilot diagnostic. Full RTH
  minute grids are required for this narrow diagnostic; the built-in calendar
  remains an engineering baseline, not new provider-authoritative schedule proof.

## Next schemas and research boundaries

Order after the approved bar pilot: `trades`, `tbbo` or `mbp-1`, then `mbp-10`,
then `mbo` only as entitled. Query fresh count/size/cost and obtain fresh approval
for each scope. Trades/quotes require side/unknown-side and bid/ask validation;
depth/MBO requires sequence/gap and reconstruction validation. The bar adapter
does not claim to ingest these schemas or supply real CVD, footprint or absorption.

One session proves plumbing only. Seek sufficient multi-contract/multi-regime
history (planning recommendation 3+ years), separate chronological development,
calibration and independently eligible evaluation, with adequate event counts.
Already-used 2024–2026 history is not an untouched holdout. No directional,
200–500-point target or competing-risk probability can be claimed from this pilot.
