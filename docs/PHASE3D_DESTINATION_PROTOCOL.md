# Fixed large-destination diagnostic protocol

Defined before running `scripts/phase3d_destinations.py`.

Use the existing NQ five-minute cache and unchanged ORB, VWAP and value signals.
Keep original strategy stops. Compare exactly 200, 350 and 500-point targets;
24 and 78-bar horizons; one and three ticks per side, $2.50 commission per side.
No geometry search or promotion. Quarantine the latest fifth of each strategy's
available signal days before reporting; prior inspection of this cache still
precludes calling the remaining sample independent final evidence.

Keep touch-after-stop distinct from target-before-stop. Same-bar ambiguity is
unscored. Incomplete RTH windows are censored unless a barrier resolves earlier;
internal gaps invalidate outcomes. Timeouts exit at observed horizon close only
when the full horizon exists. Stops gap adversely to the opening price; no
favorable limit-price improvement is assumed. Exit slippage applies on both
target and stop scenarios. Entries include entry slippage.

Report sample/date counts, outcome counts, risk/target geometry, observed event
rates and day-block intervals, and hypothetical one-contract mean net outcomes.
Do not add correlated candidate outcomes into portfolio profits. Observed rates
can be biased by censoring and are not deployable probability forecasts.
