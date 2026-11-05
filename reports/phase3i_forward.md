# Forward shadow report

Model `ndx-range-v1` - status `RESEARCH_VALIDATED_PENDING_SHADOW` - decision `NO_TRADE`

- Issued: **2**
- Matured: **1**
- Pending: **1**
- Missed sessions: **0**
- Audit failures: **1**

| Quantile | Coverage | 95% interval | Mean pinball | Baseline pinball |
|---|---:|---|---:|---:|
| p50 | 0.000 | [0.000, 0.793] | 0.001331 | not embedded at issuance |
| p80 | 1.000 | [0.207, 1.000] | 0.001309 | not embedded at issuance |
| p90 | 1.000 | [0.207, 1.000] | 0.000893 | not embedded at issuance |

Milestones: {'30': {'target': 30, 'matured': 1, 'remaining': 29, 'reached': False}, '60': {'target': 60, 'matured': 1, 'remaining': 59, 'reached': False}, '90': {'target': 90, 'matured': 1, 'remaining': 89, 'reached': False}}

Separate post-issuance, train-only comparator for `20d48fc41c2cc0f5c0ae4f2d`: pinball {'p50': 0.0026809509185644707, 'p80': 0.0009371283706551635, 'p90': 0.0013281705419723002}. This was not an embedded issued forecast; do not interpret one comparison as predictive skill.

This report separates implementation from statistical success. A running service is not evidence of accuracy.

Legacy forecasts without an inference revision omitted frozen residual adjustments. They remain immutable and are scored as issued, separately from corrected inference.
