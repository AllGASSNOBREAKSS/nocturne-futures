# Intermarket Futures, Macro Intelligence and Premarket State

## 1. Tracked core instruments

- **NQ:** Nasdaq futures; instrument traded and target-level reference for initial implementation.
- **ES:** S&P 500 futures; broader equity risk context, leadership and divergence relative to NQ.
- **VX:** Cboe Futures Exchange VIX futures; term structure and volatility risk (DO NOT substitute spot VIX or mislabel as CME VIX futures).
- **ZN and ZB:** CBOT/Treasury note/bond futures, term structure and repricing proxies; **bond futures prices do not equal Treasury yields**.

Instrument aliases, continuous rolls, exact tick metadata and calendars must come from the instrument registry rather than hardcoded strings. Cross-market lead/lag comparisons require as-of timestamp synchronization and stale data controls.

## 2. Feature hypotheses

- Rolling ES/NQ relative performance, spread beta, correlation and leadership under volatility controls.
- VX front/back futures slope, curve steepening/flattening, VIX spot–future gap only when the spot data is available and correctly timestamped.
- ZN/ZB returns, curve changes and co-movement conditional on scheduled release type; compare against actual yields from official/approved source.
- Cross-market shocks at release time, liquidity thinning, spread widening and divergence consistency.
- Regime inference conditions on data availability; avoid fixed assertions like 'NQ rises when yields fall'.

## 3. Premarket checklist output

Produce a machine-readable `PremarketState` each session: session calendar, NQ/ES overnight gap/range, previous RTH value/profile, developing overnight POC/value, ES/NQ leadership, VX term structure, ZN/ZB movements, high-impact economic calendar, mega-cap earnings risks, rollover/holiday flags, upcoming liquidity discontinuities and data-quality status.

`PRE_EVENT_LOCK`, `RELEASE_PENDING`, `RELEASE_ACTUAL_UNCONFIRMED`, `POST_RELEASE_REPRICE`, `NORMAL` should be explicit risk states based on authoritative timestamps, vendor freshness and policies. An LLM-generated news headline never directly places an order.

## 4. Point-in-time event requirements

For every economic event: `event_id, country, scheduled_at, first_available_at, expected_release, actual, prior, revised_prior, units, source, vendor_received_at, revision_seq, reliability, instruments_impacted, licensing_status`.

For unscheduled global news: first-seen timestamp, original publisher, topic/region, entity links, dedup cluster, source reliability, verified/unverified state, expiration and observed market reaction. Store headlines legally; respect permitted access and redistribution terms.

## 5. Quantitative evaluations

Run before/after event studies with realistic arrival latency, compare scheduled-only event guardrails vs event-conditioned ML and analyze performance across event type, surprise sign/size, premarket liquidity, VX state and ZN/ZB repricing. Report false alerts and missed event risk. Do not treat an unexpected headline's later article timestamp as if it preceded the move.

## 6. Staged integration

P0: scheduled official calendar and missing-event risk gates; ES/NQ bars. P1: actual/expected values, historical event vintages, authorized headlines, CFE VX and CBOT ZN/ZB aligned features. P2: event-surprise ML and real-time volatility/fill-aware reassessment if sufficient history, speed and rights exist.
