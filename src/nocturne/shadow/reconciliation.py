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
