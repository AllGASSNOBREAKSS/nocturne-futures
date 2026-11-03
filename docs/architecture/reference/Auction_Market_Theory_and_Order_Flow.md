# Auction Market Theory, Volume Profile, Market Profile, Tape and DOM — Engineering Specification

**Purpose:** Turn user-requested market concepts into deterministic feature contracts and testable strategy hypotheses. No AMT concept is proof of future price movement.

## 1. Priority and implementation status labels

- **P0 (bar + true traded volume):** RTH/ETH session boundaries, IB/opening range, true volume-weighted VWAP, OHLCV baselines.
- **P1 (true trades by price):** developing/session/composite volume profile, POC, VAH/VAL, HVN/LVN, value migration, acceptance/rejection and auction rotation.
- **P1 (time-in-price):** TPO Market Profile, TPO POC/value area, initial balance and balance area; clearly distinguish TPO from traded-volume features.
- **P2 (tick + bid/ask quotes):** trade-side inference, footprint, aggressor delta and CVD with classification confidence and reset policy.
- **P2 (L2/market-by-price):** depth imbalance, order-flow imbalance, liquidity additions/cancellations, DOM updates, spread/queue liquidity context.
- **P3 (MBO):** order-level lifecycle and optional queue analysis, only with accurate provider semantics and entitlements.

## 2. AMT state machine: research hypothesis

`PREMARKET_CONTEXT -> OPEN_CLASSIFICATION -> BALANCED | IMBALANCED | TRANSITION -> VALUE_ACCEPTED | VALUE_REJECTED -> EXPIRED`.

No state is inferred solely from visual descriptions. Formalize inputs and rules:

| State/observation | Computable feature | Leakage guard |
|---|---|---|
| Balance / rotation | intraday crossings of developing POC, realized range/volatility, rotation count, value overlap | Use only trades observed at cutoff |
| Value migration | delta of developing POC and VAH/VAL across fixed times; prior-session comparisons | Never use final-session POC before session close |
| Initial balance (IB) | time-boxed high/low, volume/range during specified RTH opening interval | Do not reference incomplete IB as final |
| Acceptance | time and actual trade volume spent beyond predefined boundary, close confirmations | Exact holding window is predetermined |
| Rejection / failed auction | excursion beyond boundary followed by return into prior value zone within explicit time | Record candidate before observing reclaim if studying live detection |
| Excess / tails | price extreme with low relative volume/TPO occupancy and subsequent rotation | Do not assume meaning without testing |
| Initiative/responsive proxy | momentum plus traded-volume/delta context relative to known value | Do not claim identified institutional intent |

## 3. Volume Profile computation contract

Session `S` consists of executed trades `i` with tick-normalized price `p_i` and quantity `q_i`.

`V_S(p) = Σ_i q_i * 1[p_i = p]`, excluding cancelled/corrected trades per vendor semantics.

- `V_S = Σ_p V_S(p)` must equal eligible traded quantity in the session; assert conservation.
- **POC:** `argmax_p V_S(p)`; specify deterministic tie-break (e.g. nearest VWAP, then lower price); make tie-break configurable and versioned.
- **Value area:** define *one explicit algorithm* (e.g. expand from POC adding contiguous adjacent bins with larger volume first, ties deterministic) until reaching `value_area_share` of volume, default research config `0.70`. Store algorithm/version; alternate implementations differ.
- **VAH/VAL:** max/min tick price in resulting contiguous value set. Do not conflate them with 70th/30th percentiles of trade prices.
- **HVN/LVN:** local maxima/minima of smoothed volume-density curve; specify smoothing window, minimum prominence and stable bin width. Report `quality=INSUFFICIENT_TRADES` when profile sparse.
- **Composite profile:** use explicit window and contract roll adjustment policy, never treat adjusted continuous futures prices as raw traded prices.
- Profiles: separate prior completed RTH/ETH, *developing* current RTH, overnight and n-session composite. `asof_ts` and `session_end_ts` must be distinct.

## 4. TPO Market Profile computation contract

`TPO_S(p) = Σ_brackets 1[price p traded during bracket]`; brackets are time slices (example: 30 minutes, configurable); a bracket contributes occupancy irrespective of traded quantity. Use a clear bin/tick size, calendar, interval and missing-data policy. Label TPO metrics `tpo_poc`, `tpo_vah`, `tpo_val` so they cannot be accidentally substituted for traded-volume values.

## 5. Tape / DOM / footprint schemas

Minimum trade: `contract, event_ts, available_ts, price_ticks, qty, trade_id, trade_conditions, aggressor_side_or_unknown, aggressor_confidence`.

Minimum quote: `contract, event_ts, available_ts, bid_px, ask_px, bid_qty, ask_qty, source_seq`.

Minimum book update: `contract, event_ts, receive_ts, source_seq, action, side, level_or_order_id, px_ticks, qty, book_reset_flag`.

**Research features:** signed executed-volume delta; CVD with explicit reset; quote- and trade-aligned imbalance; multi-level DOM imbalance; top-of-book spread; cancellations versus additions; trade-rate bursts; replenishment proxies; footprint volume by price/side; queue position *only when provider semantics allow it*.

Do not identify genuine hidden liquidity from displayed DOM, infer order intent from candles, or label spoofing from cancellations alone. Book sequence gaps and stale quotes must invalidate dependent features.

## 6. Sample strategy hypotheses to test, not deploy blindly

A. **Balance-to-imbalance auction:** confirmed trade activity outside prior value area with expanding range, durable acceptance, and regime-compatible volatility; stop based on auction invalidation, target at measured next significant volume/structure zone.

B. **VAH/VAL failed auction:** excursion across prior value boundary, return into prior value, rejection signal, controlled stop outside excursion, candidate profile node targets.

C. **Value migration trend continuation:** developing value trending with price and VWAP, pullback to established value reference, continuation on observed tape/volume confirmation.

D. **Low-volume-node traversal:** candidate fast-travel zone across historical LVN during breakout, conditioned on order book liquidity and contemporaneous volatility. No 'guaranteed LVN fill'.

E. **DOM-assisted absorption proxy:** high signed aggressive traded volume against minimal price movement plus sustained displayed replenishment; requires tick and depth history and more conservative fill costs.

For each hypothesis, implement null-control experiments, positive/negative days, counterfactual thresholds, held-out sessions, trade costs and regime stratification. Promotion criterion: incremental skill and net expected value on unseen data relative to rule-only baseline.

## 7. Tests and acceptance

Golden fixtures for: bin edges, POC ties, 70% expansion and overshoot, empty profile, developing profile, session roll, TPO-vs-volume separation, corrected trades, book reset, sequence gaps, CVD reset, failed auction deterministic rules. Add property tests asserting total volume accounting and Python/C++ parity. No usable depth feed -> feature marked unavailable, not silently approximated by standard candles.
