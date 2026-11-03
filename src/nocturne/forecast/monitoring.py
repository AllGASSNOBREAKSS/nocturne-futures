"""Descriptive journal monitoring; no automatic model promotion or rollback.

Do not treat correlated level targets or repeated forecasts as independent
observations. Group explicitly by instrument, event horizon and model lineage.
"""
from collections import Counter, defaultdict
import math


def summarize_evaluations(records):
    groups = defaultdict(list)
    for record in records:
        key = tuple(record.get(field, "unknown") for field in
                    ("instrument", "horizon", "model_version", "regime", "event_state"))
        groups[key].append(record)
    result = []
    for key, rows in sorted(groups.items()):
        matured = [row for row in rows if row["outcome"]["status"] == "EVALUATED"]
        coverage = {}
        for quantile in (50, 80, 90):
            values = [row["outcome"].get(f"p{quantile}_covered") for row in matured]
            values = [value for value in values if value is not None]
            coverage[f"p{quantile}"] = {"n": len(values), "coverage": sum(values) / len(values) if values else None}
        losses = []
        for row in matured:
            for target in row["outcome"].get("target_touches", []):
                probability, outcome = target.get("touch_probability"), target.get("touched")
                if (probability is not None and outcome is not None and
                        math.isfinite(probability) and 0 <= probability <= 1):
                    losses.append((probability - float(outcome)) ** 2)
        result.append({**dict(zip(("instrument", "horizon", "model_version", "regime", "event_state"), key)),
                       "forecasts": len(rows), "matured": len(matured),
                       "status_counts": dict(Counter(row["outcome"]["status"] for row in rows)),
                       "range_coverage": coverage, "touch_probability_pairs": len(losses),
                       "touch_brier_descriptive": sum(losses) / len(losses) if losses else None,
                       "sample_status": "NO_MATURED_FORECASTS" if not matured else "RETROSPECTIVE_ONLY",
                       "independence": "not_established; repeated forecasts and targets may overlap"})
    return {"groups": result, "decision": "NO_PROMOTION",
            "automatic_rollback": False, "drift_alerts": "UNAVAILABLE_WITHOUT_VALIDATED_REFERENCE"}
