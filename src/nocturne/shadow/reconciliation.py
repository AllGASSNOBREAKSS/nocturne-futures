"""Verify archived issuance evidence; never repair an issued prediction."""
import json
from dataclasses import replace

import pandas as pd

from ..adapters.snapshots import SnapshotStore, canonical, digest
from .features import MIN_HISTORY, build_features


def verify_issuance(forecast, archive: SnapshotStore, identifiers):
    feature_asof = forecast.get("feature_asof", forecast["created_at"])
    if pd.Timestamp(feature_asof) > pd.Timestamp(forecast["created_at"]):
        raise ValueError("feature time follows issuance")
    frames = {}
    for role, symbol in (("index", "^NDX"), ("vix", "^VIX")):
        timezone = "America/New_York" if role == "index" else "America/Chicago"
        session = "US_cash_daily" if role == "index" else "VIX_daily_context"
        manifest = archive.manifest(identifiers[role])
        source = manifest["source"]
        if (source["symbol"] != symbol or source["provider"] != "yahoo_public_unofficial"
                or source["frequency"] != "1d" or source["session"] != session
                or source["price_basis"] != "provider_quote_ohlc_not_adjclose"
                or source.get("timezone") != timezone
                or pd.Timestamp(source["received_at"]) > pd.Timestamp(feature_asof)):
            raise ValueError("issuance source identity or chronology mismatch")
        raw_meta = json.loads(archive.read_object(manifest["raw_sha256"]))["chart"]["result"][0]["meta"]
        if raw_meta.get("instrumentType") != "INDEX" or raw_meta.get("exchangeTimezoneName") != timezone:
            raise ValueError("issuance upstream instrument/session mismatch")
        frame = archive.frame(identifiers[role])
        # Match the operational loader's exact view, not merely the CSV bytes.
        frames[role] = frame[frame.source_complete.eq(True)] if "source_complete" in frame else frame
    replay = build_features(frames["index"], frames["vix"], feature_asof)
    if replay.dataset_sha256 != forecast["dataset_sha256"] and not forecast.get("dataset_digest_format"):
        # Legacy issuance used pandas' OS-default CSV newline. Support its
        # exact LF/CRLF bytes, never a numeric tolerance or a changed dataset.
        original = frames["index"].copy()
        original = original[original.available_at <= pd.Timestamp(feature_asof)]
        original["date"] = pd.to_datetime(original.date)
        original = original.sort_values("date").tail(MIN_HISTORY)[["date", "close", "high", "low", "volume"]]
        candidates = {digest(original.to_csv(index=False, lineterminator=end).encode()) for end in ("\n", "\r\n")}
        if forecast["dataset_sha256"] in candidates:
            replay = replace(replay, dataset_sha256=forecast["dataset_sha256"])
    if (replay.digest() != forecast["feature_digest"] or replay.dataset_sha256 != forecast["dataset_sha256"]
            or replay.reference_close != forecast["reference_close"] or replay.values != forecast["features"]):
        raise ValueError("archived issuance does not reproduce frozen forecast inputs")
    return frames


def reference_values(row):
    return {**{key: float(row[key]) for key in ("open", "high", "low", "close", "volume")},
            "timestamp": pd.Timestamp(row["timestamp"]).isoformat(),
            "available_at": pd.Timestamp(row["available_at"]).isoformat()}


def verify_reconciliation(forecast, record, archive, current_close, current_bar=None):
    if record.get("reconciliation_id") and record["reconciliation_id"] != digest(canonical({k: v for k, v in record.items() if k != "reconciliation_id"})):
        raise ValueError("reconciliation checksum mismatch")
    if (record["forecast_id"] != forecast["forecast_id"]
            or record["forecast_sha256"] != digest(canonical(forecast))
            or record["classification"] != "VERIFIED_AS_ISSUED_PROVIDER_REVISION"
            or record["revised_reference_close"] != current_close):
        raise ValueError("reconciliation does not bind the issued forecast/current observation")
    original = verify_issuance(forecast, archive, record["issuance_snapshot_ids"])["index"]
    revised_manifest = archive.manifest(record["revised_snapshot_id"])
    source = revised_manifest["source"]
    if (source["symbol"] != "^NDX" or source["session"] != "US_cash_daily"
            or source["price_basis"] != "provider_quote_ohlc_not_adjclose"
            or source["provider"] != "yahoo_public_unofficial"
            or pd.Timestamp(source["received_at"]) < pd.Timestamp(forecast["created_at"])):
        raise ValueError("revised source conventions/chronology mismatch")
    revised = archive.frame(record["revised_snapshot_id"])
    a = original[original.date == forecast["data_date"]].iloc[0]
    b = revised[revised.date == forecast["data_date"]].iloc[0]
    if b.close != current_close or pd.Timestamp(a.timestamp) != pd.Timestamp(b.timestamp):
        raise ValueError("reference close/session timestamp mismatch")
    if record.get("revised_reference_bar_sha256"):
        if digest(canonical(reference_values(b))) != record["revised_reference_bar_sha256"]:
            raise ValueError("revised reference bar seal mismatch")
        if current_bar is None or reference_values(current_bar) != reference_values(b):
            raise ValueError("current reference observation is not the reconciled bar")
    # Verify upstream timezone/instrument conventions, not just the CSV label.
    metas = []
    for identifier in (record["issuance_snapshot_ids"]["index"], record["revised_snapshot_id"]):
        m = archive.manifest(identifier)
        metas.append(json.loads(archive.read_object(m["raw_sha256"]))["chart"]["result"][0]["meta"])
    for key in ("symbol", "instrumentType", "exchangeTimezoneName", "dataGranularity"):
        if metas[0].get(key) != metas[1].get(key) or metas[0].get(key) is None:
            raise ValueError("upstream instrument/session conventions changed")
    return True


def investigate_revision(forecast, archive, revised_id, now):
    """Build a proof candidate from embedded issuance evidence; write nothing."""
    if pd.Timestamp(now).tzinfo is None:
        raise ValueError("timezone-aware investigation time required")
    seal = forecast.get("record_sha256")
    if not seal or seal != digest(canonical({k: v for k, v in forecast.items() if k != "record_sha256"})):
        raise ValueError("sealed forecast required for generic reconciliation")
    identifiers = forecast["market_snapshot_ids"]
    original = verify_issuance(forecast, archive, identifiers)["index"]
    revised = archive.frame(revised_id)
    a = original[original.date == forecast["data_date"]].iloc[0]
    b = revised[revised.date == forecast["data_date"]].iloc[0]
    if b.source_complete not in (True, "True"):
        raise ValueError("revised reference is incomplete")
    manifest = archive.manifest(revised_id)
    if pd.Timestamp(manifest["source"]["received_at"]) > pd.Timestamp(now):
        raise ValueError("revised receipt follows investigation")
    def details(identifier):
        m = archive.manifest(identifier)
        value = json.loads(archive.read_object(m["raw_sha256"]))["chart"]["result"][0]
        indices = [i for i, stamp in enumerate(value["timestamp"])
                   if pd.Timestamp(stamp, unit="s", tz="UTC").date().isoformat() == forecast["data_date"]]
        if len(indices) != 1:
            raise ValueError("reference session not unique in upstream response")
        i = indices[0]
        quote = value["indicators"]["quote"][0]
        adjusted = value["indicators"].get("adjclose", [{}])[0].get("adjclose", [])
        adjusted_close = adjusted[i] if adjusted else None
        if adjusted_close is not None and adjusted_close != quote["close"][i]:
            raise ValueError("adjusted/quote close convention needs separate review")
        return {"snapshot_id": identifier, "source": m["source"], "raw_sha256": m["raw_sha256"],
                "normalized_sha256": m["normalized_sha256"], "exchange_timestamp": value["timestamp"][i],
                "quote": {key: values[i] for key, values in quote.items()}, "adjusted_close": adjusted_close,
                "metadata": {key: value["meta"].get(key) for key in ("symbol", "instrumentType", "exchangeTimezoneName", "dataGranularity")}}
    original_detail, revised_detail = details(identifiers["index"]), details(revised_id)
    record = {"forecast_id": forecast["forecast_id"], "forecast_sha256": digest(canonical(forecast)),
              "issuance_snapshot_ids": identifiers, "revised_snapshot_id": revised_id,
              "revised_reference_close": float(b.close), "revised_reference_bar_sha256": digest(canonical(reference_values(b))),
              "classification": "VERIFIED_AS_ISSUED_PROVIDER_REVISION", "recorded_at": pd.Timestamp(now).isoformat(),
              "exchange_finality_confirmed": False, "trading_decision": "NO_TRADE",
              "policy": "score issued quantiles against original denominator; never rewrite forecasts",
              "root_cause": "upstream source values changed; provider internal reason unconfirmed"}
    verify_reconciliation(forecast, record, archive, float(b.close), current_bar=b)
    return {"record": record, "original_source": original_detail, "revised_source": revised_detail,
            "changes": {key: {"original": reference_values(a)[key], "revised": reference_values(b)[key]}
                        for key in reference_values(a) if reference_values(a)[key] != reference_values(b)[key]},
            "issuance_features_exactly_reproduced": True}


def incident_disposition(forecast, archive, revised_id, now, source_checks=()):
    """Read-only incident classification, NOT an applied reconciliation proof.

    Reuses exact issuance/raw-bar verification. Public close-only checks cannot
    authenticate final outcome high/low. This report cannot authorize evaluation,
    even if a caller supplies a purported `verified` flag in source_checks.
    A new independent outcome source needs its own reviewed evidence contract.
    """
    from datetime import timedelta
    from .calendar import session_close
    import numpy as np

    proof = investigate_revision(forecast, archive, revised_id, now)
    current = archive.frame(revised_id)
    target = pd.Timestamp(forecast['target_date'])
    bound = (target.tz_localize('UTC') + timedelta(days=1))
    rows = current[pd.to_datetime(current.date).dt.strftime('%Y-%m-%d') == forecast['target_date']]
    target_info = {'target_date': forecast['target_date'], 'availability_bound': bound.isoformat(),
                   'time_bound_elapsed': bool(pd.Timestamp(now) >= bound), 'rows': len(rows),
                   'provider_observed': False, 'independently_verified_final_ohlc': False}
    if len(rows) == 1:
        row = rows.iloc[0]
        prices = np.asarray([row.open, row.high, row.low, row.close], dtype=float)
        complete = bool(row.source_complete in (True, 'True') and np.isfinite(prices).all()
                        and (prices > 0).all() and row.high >= max(row.open, row.close, row.low)
                        and row.low <= min(row.open, row.close, row.high)
                        and pd.Timestamp(row.available_at) >= session_close(target.date()))
        target_info.update(provider_observed=True, provider_ohlc_complete=complete,
                           available_at=pd.Timestamp(row.available_at).isoformat(),
                           source_received_at=archive.manifest(revised_id)['source']['received_at'],
                           available_now=bool(complete and pd.Timestamp(now) >= max(bound, pd.Timestamp(row.available_at))),
                           bar_sha256=digest(canonical(reference_values(row))))
    original = proof['original_source']
    revised = proof['revised_source']
    a, b = float(forecast['reference_close']), float(proof['record']['revised_reference_close'])
    reasons = ['INDEPENDENT_FINAL_OUTCOME_OHLC_NOT_VERIFIED', 'REFERENCE_REVISION_NOT_APPLIED']
    if not target_info['time_bound_elapsed']:
        reasons.append('TARGET_AVAILABILITY_BOUND_NOT_REACHED')
    if not target_info.get('available_now', False):
        reasons.append('COMPLETE_AVAILABLE_TARGET_BAR_NOT_ESTABLISHED')
    return {'schema': 1, 'recorded_at': pd.Timestamp(now).isoformat(),
            'forecast_id': forecast['forecast_id'], 'forecast_sha256': digest(canonical(forecast)),
            'target_date': forecast['target_date'], 'reference_date': forecast['data_date'],
            'original_reference_close': a, 'revised_reference_close': b,
            'difference_points': b - a, 'difference_fraction_original': (b - a) / a,
            'source_timestamps': {'issued_at': forecast['created_at'],
                                  'original_received_at': original['source']['received_at'],
                                  'revised_received_at': revised['source']['received_at'],
                                  'original_exchange_timestamp': original['exchange_timestamp'],
                                  'revised_exchange_timestamp': revised['exchange_timestamp']},
            'classification': 'OBSERVED_PROVIDER_REVISION_FINALITY_UNVERIFIED',
            'cause_assessment': {'changed_upstream_payload': bool(proof['changes']),
                                 'session_identity': 'MATCHED_ARCHIVED_INSTRUMENT_TIMEZONE_TIMESTAMP',
                                 'adjustment_convention': 'QUOTE_EQUALS_ADJCLOSE_IN_INSPECTED_REFERENCE_ROWS',
                                 'issuance_inputs': 'EXACTLY_REPRODUCED',
                                 'provider_internal_cause': 'UNCONFIRMED',
                                 'numerical_software_defect': 'NOT_EVIDENCED_BY_SOURCE_REVISION; SEE_SEPARATE_FROZEN_INFERENCE_REPLAY'},
            'independent_evidence': list(source_checks), 'outcome_observation': target_info,
            'verdict': 'AUDIT_BLOCKED', 'eligible_for_evaluation': False,
            'blocking_reasons': reasons, 'reconciliation_applied': False,
            'provider_revision_evidence': proof, 'trading_decision': 'NO_TRADE',
            'limits': 'Classification is not independent final OHLC verification, an evaluation override or permission to change original forecasts/denominators.'}
