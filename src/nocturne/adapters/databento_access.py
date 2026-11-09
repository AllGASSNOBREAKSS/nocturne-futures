"""Metadata-only pilot preflight and explicit, request-bound consumption approval.

Official HTTP reference: https://databento.com/docs/api-historical
Metadata/symbology are free according to that reference; time series are metered.
An offered schema, quote, API key or advertised credit is not spending permission.
"""
import json
import os
import re
from decimal import Decimal

import pandas as pd
import requests

from .snapshots import canonical, digest, immutable_write

BASE = "https://hist.databento.com/v0/"
SCHEMAS = ("ohlcv-1m", "trades", "tbbo", "mbp-1", "mbp-10", "mbo")


def pilot_request(contract, instrument, start, end):
    if instrument not in ("NQ", "ES") or not re.fullmatch(re.escape(instrument) + r"[HMUZ]\d{1,4}", contract):
        raise ValueError("one explicit NQ/ES quarterly raw contract required")
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    if start.tzinfo is None or end.tzinfo is None or not pd.Timedelta(0) < end - start <= pd.Timedelta("1D"):
        raise ValueError("pilot must have timezone-aware bounds of at most one day")
    return {"dataset": "GLBX.MDP3", "symbols": contract, "schema": "ohlcv-1m", "stype_in": "raw_symbol",
            "start": start.tz_convert("UTC").isoformat(), "end": end.tz_convert("UTC").isoformat()}


class DatabentoAccess:
    def __init__(self, key=None, transport=None):
        self.key = key or os.environ.get("DATABENTO_API_KEY")
        self.transport = transport or requests.Session()

    def _call(self, method, parameters, archive):
        if not self.key:
            raise ValueError("DATABENTO_API_KEY missing")
        if method not in {"metadata.list_datasets", "metadata.list_schemas", "metadata.get_dataset_range",
                          "metadata.get_dataset_condition", "metadata.get_record_count", "metadata.get_billable_size",
                          "metadata.list_unit_prices",
                          "metadata.get_cost", "symbology.resolve"}:
            raise ValueError("only non-consumption metadata/symbology methods allowed")
        response = (self.transport.post(BASE + method, data=parameters, auth=(self.key, ""), timeout=(10, 30))
                    if method == "symbology.resolve" else
                    self.transport.get(BASE + method, params=parameters, auth=(self.key, ""), timeout=(10, 30)))
        # Do not persist URLs, auth headers, HTTP error bodies or exception strings.
        if response.status_code != 200:
            raise ValueError(f"METADATA_HTTP_{response.status_code}")
        data = response.json()
        body = response.content
        identifier = digest(body)
        immutable_write(archive / "objects" / identifier, body)
        return data, {"method": method, "parameters": parameters, "body_sha256": identifier,
                      "received_at": pd.Timestamp.now(tz="UTC").isoformat()}

    def preflight(self, root, *, contract, instrument, start, end):
        from pathlib import Path
        root = Path(root)
        request = pilot_request(contract, instrument, start, end)
        report = {"request": request, "instrument": instrument, "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
                  "status": "DATA_BLOCKED", "cost_usd": None, "billable_bytes": None, "record_count": None,
                  "credit_eligibility": "ACCOUNT_SPECIFIC_UNVERIFIED", "consumption_authorized": False,
                  "metadata_receipts": [], "time_series_requested": False}
        if not self.key:
            report["reason"] = "DATABENTO_API_KEY_MISSING"
            return report
        def call(method, params):
            value, receipt = self._call(method, params, root)
            report["metadata_receipts"].append(receipt)
            return value
        try:
            datasets = call("metadata.list_datasets", {})
            if "GLBX.MDP3" not in datasets:
                raise ValueError("DATASET_NOT_LISTED")
            schemas = call("metadata.list_schemas", {"dataset": "GLBX.MDP3"})
            report["schema_offerings"] = {s: s in schemas for s in SCHEMAS}
            if "ohlcv-1m" not in schemas:
                raise ValueError("OHLCV_SCHEMA_NOT_LISTED")
            available = call("metadata.get_dataset_range", {"dataset": "GLBX.MDP3"})
            report["available_range"] = available
            span = available.get("schema", available.get("range_by_schema", {})).get("ohlcv-1m")
            if not span or not pd.Timestamp(span["start"]) <= pd.Timestamp(request["start"]) < pd.Timestamp(request["end"]) <= pd.Timestamp(span["end"]):
                raise ValueError("PILOT_OUTSIDE_ENTITLED_SCHEMA_RANGE")
            start_date = pd.Timestamp(request["start"]).date().isoformat()
            end_date = (pd.Timestamp(request["end"]).ceil("D")).date().isoformat()
            condition = call("metadata.get_dataset_condition", {"dataset": "GLBX.MDP3", "start_date": start_date,
                                                                  "end_date": pd.Timestamp(request["end"]).date().isoformat()})
            report["dataset_conditions"] = condition
            required_dates = set(pd.date_range(pd.Timestamp(request["start"]).normalize(), pd.Timestamp(request["end"]) - pd.Timedelta("1ns"), freq="D").strftime("%Y-%m-%d"))
            good_dates = {entry["date"] for entry in condition if entry.get("condition") == "available"}
            if not required_dates <= good_dates:
                raise ValueError("PILOT_DATASET_CONDITION_UNAVAILABLE_OR_DEGRADED")
            mapping = call("symbology.resolve", {"dataset": "GLBX.MDP3", "symbols": contract,
                           "stype_in": "raw_symbol", "stype_out": "instrument_id", "start_date": start_date, "end_date": end_date})
            intervals = mapping.get("result", {}).get(contract, [])
            if mapping.get("partial") or mapping.get("not_found") or mapping.get("status") != 0 or not intervals:
                raise ValueError("RAW_CONTRACT_NOT_FULLY_RESOLVED")
            ids = {str(entry["s"]) for entry in intervals}
            covered = set()
            for entry in intervals:
                covered.update(pd.date_range(entry["d0"], entry["d1"], inclusive="left", freq="D").strftime("%Y-%m-%d"))
            if len(ids) != 1 or not next(iter(ids)).isdigit() or not required_dates <= covered:
                raise ValueError("CONTRACT_MAPPING_CHANGED_OR_INCOMPLETE")
            report["resolved_instrument_id"] = int(next(iter(ids)))
            report["symbology"] = mapping
            for field, endpoint in (("record_count", "metadata.get_record_count"), ("billable_bytes", "metadata.get_billable_size"), ("cost_usd", "metadata.get_cost")):
                value = call(endpoint, request)
                amount = Decimal(str(value))
                if not amount.is_finite() or amount < 0 or (field != "cost_usd" and amount != int(amount)):
                    raise ValueError("INVALID_PROVIDER_SIZE_OR_COST")
                report[field] = str(amount) if field == "cost_usd" else int(amount)
            if not 0 < report["record_count"] <= 1440:
                raise ValueError("EMPTY_OR_OVERSIZED_MINUTE_PILOT")
            report["status"] = "QUOTED_AWAITING_OPERATOR_APPROVAL"
        except (ValueError, KeyError, TypeError, ArithmeticError, requests.RequestException) as exc:
            report["reason"] = str(exc) if isinstance(exc, ValueError) and re.fullmatch(r"[A-Z_0-9]+", str(exc)) else type(exc).__name__
        report["quote_id"] = digest(canonical(report))
        immutable_write(root / "quotes" / f"{report['quote_id']}.json", canonical(report))
        return report


def check_approval(quote, approval, request, instrument, now=None):
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    identifier = quote.get("quote_id")
    if not identifier or digest(canonical({k: v for k, v in quote.items() if k != "quote_id"})) != identifier:
        raise ValueError("quote hash mismatch")
    if (quote.get("status") != "QUOTED_AWAITING_OPERATOR_APPROVAL" or quote["request"] != request
            or quote["instrument"] != instrument or not quote.get("metadata_receipts")
            or not isinstance(quote.get("resolved_instrument_id"), int)):
        raise ValueError("quote does not authorize this resolved request")
    generated = pd.Timestamp(quote["generated_at"])
    approved = pd.Timestamp(approval["approved_at"])
    expires = pd.Timestamp(approval["expires_at"])
    if any(stamp.tzinfo is None for stamp in (now, generated, approved, expires)):
        raise ValueError("approval chronology must be timezone aware")
    if not generated <= approved <= now < expires <= generated + pd.Timedelta("24h"):
        raise ValueError("quote/approval expired or chronology invalid")
    if approval.get("quote_id") != identifier or approval.get("authorized") is not True or not approval.get("operator_reference"):
        raise ValueError("explicit operator approval required, including zero-cost or credit usage")
    maximum, quoted = Decimal(str(approval["max_cost_usd"])), Decimal(str(quote["cost_usd"]))
    if not maximum.is_finite() or not quoted.is_finite() or not 0 <= quoted <= maximum:
        raise ValueError("provider quote exceeds approved cost")
    if type(approval.get("max_billable_bytes")) is not int or not 0 <= quote["billable_bytes"] <= approval["max_billable_bytes"]:
        raise ValueError("provider size exceeds approved budget")
    return {"quote_id": identifier, "approval_sha256": digest(canonical(approval)), "quoted_cost_usd": str(quoted),
            "authorized_at": now.isoformat(),
            "resolved_instrument_id": quote["resolved_instrument_id"],
            "warning": "provider estimate, not a provider-enforced final-invoice cap"}
