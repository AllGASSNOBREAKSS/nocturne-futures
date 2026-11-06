# Forward shadow report

Model `ndx-range-v1` - status `RESEARCH_VALIDATED_PENDING_SHADOW` - decision `NO_TRADE`

- Issued: **3**
- Matured: **2**
- Pending: **1**
- Missed sessions: **0**
- Audit failures: **0**

| Quantile | Coverage | 95% interval | Mean pinball | Baseline pinball |
|---|---:|---|---:|---:|
| p50 | 0.000 | [0.000, 0.658] | 0.009390 | 0.018739 |
| p80 | 0.500 | [0.095, 0.905] | 0.011311 | 0.021944 |
| p90 | 0.500 | [0.095, 0.905] | 0.009766 | 0.016950 |

Milestones: {'30': {'target': 30, 'matured': 2, 'remaining': 28, 'reached': False}, '60': {'target': 60, 'matured': 2, 'remaining': 58, 'reached': False}, '90': {'target': 90, 'matured': 2, 'remaining': 88, 'reached': False}}

Separate post-issuance, train-only comparator for `20d48fc41c2cc0f5c0ae4f2d`: pinball {'p50': 0.0026809509185644707, 'p80': 0.0009371283706551635, 'p90': 0.0013281705419723002}. This was not an embedded issued forecast; do not interpret one comparison as predictive skill.

This report separates implementation from statistical success. A running service is not evidence of accuracy.

Legacy forecasts without an inference revision omitted frozen residual adjustments. They remain immutable and are scored as issued, separately from corrected inference.
