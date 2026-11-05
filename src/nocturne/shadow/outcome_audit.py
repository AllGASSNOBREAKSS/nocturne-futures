"""Verify journaled outcomes from immutable source evidence, without rewriting."""
import math
import json

import pandas as pd

from ..adapters.snapshots import canonical, digest
from .calendar import session_close
from .reconciliation import verify_issuance, verify_reconciliation
from .service import session_open
from .service import _prepared

QUANTILES = {"p50": .5, "p80": .8, "p90": .9}


def pinball(actual, prediction, quantile):
    residual = actual - prediction
    return max(quantile * residual, (quantile - 1) * residual)


def audit_outcomes(store, archive, baseline=None):
    forecasts = {f["forecast_id"]: f for f in store.forecasts()}
    reconciliations = {r["reconciliation_id"]: r for r in store.reconciliations()}
    results = []
    seen = set()
    for outcome in store.outcomes():
        identifier = outcome["forecast_id"]
        checked = {"forecast_id": identifier, "status": "AUDIT_BLOCKED", "issues": []}
        try:
            if identifier in seen:
                raise ValueError("duplicate outcome ID")
            seen.add(identifier)
            forecast = forecasts[identifier]
            if outcome["forecast_sha256"] != digest(canonical(forecast)):
                raise ValueError("issued forecast hash mismatch")
            if forecast.get("record_sha256") and forecast["record_sha256"] != digest(canonical({k: v for k, v in forecast.items() if k != "record_sha256"})):
                raise ValueError("forecast seal mismatch")
            day = pd.Timestamp(outcome["target_date"]).date()
            issued, evaluated = pd.Timestamp(forecast["created_at"]), pd.Timestamp(outcome["evaluated_at"])
            if (outcome["target_date"] != forecast["target_date"] or issued >= session_open(day)
                    or evaluated < session_close(day)):
                raise ValueError("forecast/outcome horizon chronology mismatch")
            manifest = archive.manifest(outcome["market_snapshot_id"])
            source = manifest["source"]
            if (source["symbol"] != "^NDX" or source["provider"] != "yahoo_public_unofficial"
                    or source["session"] != "US_cash_daily" or source["frequency"] != "1d"
                    or source["price_basis"] != "provider_quote_ohlc_not_adjclose"
                    or source["timezone"] != "America/New_York"
                    or pd.Timestamp(source["received_at"]) > evaluated):
                raise ValueError("outcome source identity or receipt chronology mismatch")
            frame = archive.frame(outcome["market_snapshot_id"])
            raw_meta = json.loads(archive.read_object(manifest["raw_sha256"]))["chart"]["result"][0]["meta"]
            if (raw_meta.get("symbol") != "^NDX" or raw_meta.get("instrumentType") != "INDEX"
                    or raw_meta.get("exchangeTimezoneName") != "America/New_York"):
                raise ValueError("upstream outcome identity mismatch")
            if frame.date.duplicated().any():
                raise ValueError("duplicate source dates")
            bar = frame[frame.date == outcome["target_date"]].iloc[0]
            available = pd.Timestamp(bar.available_at)
            prices = [float(bar[k]) for k in ("open", "high", "low", "close")]
            if (not all(math.isfinite(x) and x > 0 for x in prices)
                    or bar.source_complete not in (True, "True") or bar.high < max(prices) or bar.low > min(prices)
                    or pd.Timestamp(bar.timestamp) != session_open(day)
                    or not session_close(day) <= available <= evaluated
                    or pd.Timestamp(outcome["source_available_at"]) != available):
                raise ValueError("incomplete/inconsistent outcome bar")
            encoded_bar = next(row for row in _prepared(frame).itertuples(index=False)
                               if row.date.date().isoformat() == outcome["target_date"])
            if digest(str(encoded_bar).encode()) != outcome["outcome_bar_sha256"]:
                raise ValueError("journaled outcome bar hash mismatch")
            if outcome["status"] != "MATURED" or outcome["data_quality_status"] != "PASSED":
                raise ValueError("outcome was not quality-approved at maturation")
            if forecast.get("market_snapshot_ids"):
                verify_issuance(forecast, archive, forecast["market_snapshot_ids"])
            reference = frame[frame.date == forecast["data_date"]].iloc[0]
            if not forecast.get("market_snapshot_ids") or float(reference.close) != forecast["reference_close"]:
                proofs = outcome.get("reconciliation_ids", [])
                if not proofs or not any(verify_reconciliation(forecast, reconciliations[p], archive, float(reference.close)) for p in proofs):
                    raise ValueError("unverified reference revision")
            actual_points = float(bar.high - bar.low)
            actual = actual_points / forecast["reference_close"]
            checks = {"realized_high": float(bar.high), "realized_low": float(bar.low),
                      "realized_range_points": actual_points, "realized_range_pct": actual,
                      "reference_close": forecast["reference_close"]}
            for key, value in checks.items():
                if not math.isclose(float(outcome[key]), value, rel_tol=0, abs_tol=1e-12):
                    raise ValueError(f"journaled {key} differs from immutable evidence")
            losses = {}
            for name, q in QUANTILES.items():
                value = forecast["quantiles"][name]
                losses[name] = pinball(actual, value, q)
                if (outcome["covered"][name] != (actual <= value)
                        or not math.isclose(outcome["pinball"][name], losses[name], rel_tol=0, abs_tol=1e-12)
                        or not math.isclose(outcome["forecast_points"][name], value * forecast["reference_close"], rel_tol=0, abs_tol=1e-9)):
                    raise ValueError("coverage, pinball or point-conversion mismatch")
            comparator = forecast.get("baseline_quantiles") or baseline
            comparison = None
            if comparator:
                comparison = {"registration": "EMBEDDED_AT_ISSUANCE" if forecast.get("baseline_quantiles") else "POST_ISSUANCE_FROZEN_TRAIN_ONLY_COMPARATOR_NOT_AN_ISSUED_FORECAST",
                              "quantiles": comparator,
                              "pinball": {name: pinball(actual, comparator[name], q) for name, q in QUANTILES.items()}}
            checked.update(status="VERIFIED_RESEARCH_GRADE", source_reliability="unofficial_provider_not_independently_exchange_confirmed",
                           target_date=outcome["target_date"], **checks,
                           covered=outcome["covered"], pinball=losses, baseline_comparison=comparison,
                           forecast_sha256=outcome["forecast_sha256"], outcome_sha256=digest(canonical(outcome)),
                           snapshot_id=outcome["market_snapshot_id"], raw_sha256=manifest["raw_sha256"],
                           source_close=float(bar.close),
                           normalized_sha256=manifest["normalized_sha256"], source_received_at=source["received_at"],
                           source_available_at=available.isoformat(), evaluated_at=evaluated.isoformat(),
                           inference_revision=forecast.get("inference_revision", "legacy-unadjusted"))
        except (KeyError, ValueError, TypeError, OSError, IndexError) as exc:
            checked["issues"].append(str(exc))
        results.append(checked)
    bad_ids = {r["forecast_id"] for r in results if r["status"] != "VERIFIED_RESEARCH_GRADE"}
    for checked in results:
        if checked["forecast_id"] in bad_ids and checked["status"] == "VERIFIED_RESEARCH_GRADE":
            checked["status"] = "AUDIT_BLOCKED"
            checked["issues"].append("another record for this forecast failed verification")
    valid = [r for r in results if r["status"] == "VERIFIED_RESEARCH_GRADE"]
    return {"status": "AUDIT_BLOCKED" if len(valid) != len(results) else "VERIFIED_RESEARCH_GRADE" if valid else "NO_MATURED_OUTCOMES",
            "journaled": len(results), "verified": len(valid), "records": results,
            "sample_warning": "descriptive observations only; no forward calibration or trading-edge claim",
            "trading_decision": "NO_TRADE"}
