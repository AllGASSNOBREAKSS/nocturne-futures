# Phase 3K — revision-safe source evidence

Checkpoint: 2026-11-04 UTC. Branch `feat/phase3k`, base `9f68c6b`.
Only `ndx-range-v1` is shadow-active; trading remains **NO_TRADE**.

## 1. Verified starting point

The clean Phase 3J tree reproduced **253 passing tests including C++ parity**.
Both reported commits were verified green; latest Phase 3J run:
https://github.com/AllGASSNOBREAKSS/nocturne-futures/actions/runs/41778379758
The November 4 target session has not opened at this checkpoint. The latest real
NDX/VIX acquisitions still end November 3. No matured outcome was manufactured.

## 2. Investigation: a genuine upstream OHLCV payload revision

The original committed research receipt for NDX is
`2026-11-04T02:00:32.198490+00:00`; VIX was received at `02:00:37.437173+00:00`.
Both predate forecast issuance at `2026-11-04T02:53:30.237804+00:00` (November 3
21:53 New York time). Original raw and normalized checksums passed.

The archived NDX raw JSON hash is
`5d7935b96df1c09a65fe71497782a6e700d4fbc9402495935ac8efe2dc2c7212`;
normalized hash is
`76af8a691b4b8af090630f002d78064f0442ebdb753c3e104b6fb6eeffdb073e`.
Replaying **original archived inputs only** exactly reproduced the stored
reference, all eleven features, feature digest and input dataset digest. This is
input-provenance verification, not regeneration of an issued prediction.

The November 3 raw payload changed as follows:

- Open and low: 28085.49609375 → 28085.5.
- High: 28307.8984375 → 28307.900390625.
- Close: 28180.263671875 → 28180.259765625.
- Volume: 1,304,372,000 → 8,347,090,000.

Only one overlapping historical observation changed. The date, provider bar
timestamp `1793716200`, INDEX identity, New York timezone, daily granularity and
regular-market timestamp remained unchanged. Adjusted close equals quote close
on the disputed observation in both payloads; the implementation used quote
OHLC, not adjusted close. No evidence of a local parser, timestamp or adjustment-
column substitution explains this difference. Prices resemble a precision
revision, but the much larger volume change cannot be explained by rounding.

**Classification: VERIFIED_AS_ISSUED_PROVIDER_REVISION.** The provider response
really changed; Yahoo's internal reason (e.g. finalization or correction) is
unconfirmed. This classification does not establish either value as official
exchange truth. The original value was demonstrably the research source's value
available to this forecast under its documented as-issued contract.

Independent checks did not establish a competing value: the bounded FRED
`NASDAQ100` CSV request failed with `ConnectionError`; the public Nasdaq index
history endpoint returned HTTP 404. Neither was bypassed. FRED, if accessible,
would be a separate distributor of Nasdaq-origin close data, not necessarily an
independent upstream measurement, and cannot verify daily high/low or original
availability. Full attempts and evidence hashes are in
`reports/phase3k_reconciliation.json`.

## 3. Reconciliation without rewriting the forecast

`scripts/phase3k_reconcile.py` verifies receipts, replays archived inputs, compares
source conventions and appends a separate hash-bound reconciliation to
`data/shadow/ndx_range/reconciliations.jsonl`. It writes no forecasts or outcomes.
The audit re-verifies evidence each cycle; a reconciliation cannot waive other
integrity failures, a changed forecast, missing archives or a different revised
reference. Earlier investigation records remain append-only; only a record
passing the current full verification is usable.

NDX is a New York cash-session index; Yahoo labels VIX's source timezone
America/Chicago. VIX is explicitly separate daily context, not an assertion that
its session matches NDX. These provider identities are checked in archived raw
metadata as well as normalized provenance.

The original forecast line is byte-identical to the previous checkpoint, SHA-256
`61f4034a108ccf6545959d4dac39e18ae3c5247ae4557dddf9e9a8158113a1b3`.
Its percentage fractions and point conversions are unchanged. The first legacy
unadjusted forecast remains distinct from corrected residual-calibrated inference.

The specific reference mismatch is now reconciled **as issued**, not ignored via
a wider tolerance. Any eventual range remains `(actual_high - actual_low) /
28180.263671875`; the revised source close is never substituted. Outcome records
will link the original forecast hash, actual source snapshot, and the specific
verified reconciliation ID. Yahoo remains an unofficial research source, not a
certified final exchange feed.

## 4. Immutable acquisition and model evidence

`adapters/snapshots.py` adds a content-addressed object store with:

- Immutable parsed raw payloads, normalized CSVs and new HTTP response bodies.
- Source identity, frequency, price basis, session/timezone, license scope and
  original receipt time; separate archive-import time avoids backdating evidence.
- Hash-verified manifests and dataset-version identifiers.
- Raw-to-normalized value/timestamp/completeness checks, not just matching hashes.
- Append-only old/new snapshot links and exact overlapping OHLCV comparisons.
- Older archival imports cannot regress the live source head. Same-receipt
  conflicting observations are rejected rather than declared valid revisions.

For legacy imports, only canonical parsed JSON survives; original HTTP response
bytes were not retained. For new fetches, the `wire_sha256` field hashes
`requests.Response.content`: the exact decoded HTTP entity body, not TLS packets
or compressed transport bytes. No stronger transport attestation is claimed.

The mutable normalized file and manifest are cache pointers only. Production
loading must verify their exact immutable snapshot and receipt; a broken archive
fails closed. Frozen research has an explicit `FROZEN` guard that rejects refresh
before any network request. Old research bytes are not migrated or overwritten.

Every newly issued runtime forecast links both NDX and VIX snapshot IDs and a
whole-record canonical hash. Frozen weights are pinned by exact binary checksum;
metadata and baseline use canonical JSON checksums to tolerate Git newline
conversion without tolerating semantic changes. In-place `save_artifact` over a
pinned model is prohibited. No model was refitted or silently replaced.

New feature-input CSV digests explicitly use LF on every host. The legacy
verifier reproduces the exact original LF/CRLF serialization when no format was
declared, never changes values or waives a hash mismatch. Feature definitions and
model weights are unchanged.

Hashing detects corruption and accidental changes, not a privileged attacker
rewriting every object and trust anchor. Restrict write permissions and back up
the complete archive and journals. Operational archives remain local/private in
ignored `data/shadow/market/`; Git alone does **not** back them up. A new host
needs an authorized transfer of the referenced archive, not just the repo.

## 5. Multi-source checks, futures readiness and research boundaries

`source_comparison.py` requires equivalent instrument, kind, session, timezone,
price basis, currency and frequency. It refuses ETF/index substitution and
requires explicit absolute tolerances for every shared field. Differences,
source hashes and unresolved conflicts remain visible; agreement within a
threshold does not identify an authoritative feed or promote a model.

Databento/FRED/BLS/Nasdaq Data Link keys were checked by presence only and remain
absent. No purchase or billable request was made. The existing raw-contract
pipeline, licensing gates and 1m/5m target labels are preserved. Storage planning
estimates are now explicit in the provider report and requirements document;
they are not fabricated downloads or provider cost estimates.

Authentic trades, bid/ask, volume at price, CVD, DOM/MBO, VX futures and authorized
PIT economic consensus/news remain blocked. No new empirical directional model,
order-flow feature ablation or target-probability promotion was possible. Do not
repeat failed OHLCV feature families or reuse unaudited Phase 3F probability
composition as evidence. Existing purged validation interfaces remain intact.

## 6. Operations, evidence and next milestone

Existing Windows scheduling, least-privilege unattended installer support,
restart/deadline recovery and immutable journals remain. Added read-only
`/v1/data/revisions` and `/v1/data/reconciliations` endpoints. Revision warnings
and reconciliation proofs are visible in the normal shadow audit/report. The
monitor retained historical alert events and resolved active audit alerts only
after fresh verified cycles. No credentials, account privileges or task principal
were changed; no external paging or logout-independent deployment is claimed.
Acquisition incidents encountered while enabling the new snapshot guard remain
in the quality/log history, including a legacy cache lacking a snapshot ID after
a development refresh failure. They were fixed without deleting history and are
not forecast-performance losses. A real updated task-wrapper cycle exited 0
after the evidence checks passed, while recording zero matured outcomes.

Current forward sample: **1 issued, 0 matured, 1 awaiting outcome, 0 missed**.
The original first record has no pre-issued comparator embedded; baseline results
remain null rather than retroactively presented as pre-issued forecasts. The
30/60/90 monitoring milestones are unchanged, not achieved validation claims.

Local verification: **264 passed including native C++ parity**; TypeScript
typecheck passed. New tests cover response-body preservation, corruption,
normalization/identity mismatches, chronological replay, revision lineage,
immutable writes, frozen research guards, original-record integrity, model
checksum failure, cross-source equivalence and explicit tolerances. Remote CI
must be checked for this phase's commit, not inferred from Phase 3J.

Next: maintain verified scheduled acquisitions; after the November 4 session
finishes and the adapter availability bound passes (November 5 00:00 UTC), append
the first outcome only if completed-bar quality and all evidence checks pass.
Do not claim coverage or pinball from zero observations, or model accuracy from
one. Obtain licensed contract data before genuine NQ/ES empirical advancement.
