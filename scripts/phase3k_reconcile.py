"""Reproduce the original issuance inputs, then record a separate source revision.

No forecasts or outcomes are written. This is not authoritative exchange finality.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from nocturne.adapters.snapshots import SnapshotStore, canonical, compare_daily, digest
from nocturne.shadow import ShadowStore
from nocturne.shadow.reconciliation import verify_issuance, verify_reconciliation

ROOT = Path(__file__).resolve().parents[1]
MARKET = ROOT / "data/shadow/market"


def import_existing(directory, symbol, archive):
    name = symbol.replace("^", "IDX_")
    manifest = json.loads((directory / "manifests" / f"{name}.json").read_text())
    raw = (directory / "raw" / f"{name}_{manifest['raw_sha256']}.json").read_bytes()
    normalized = (directory / "normalized" / f"{name}.csv").read_bytes()
    if digest(raw) != manifest["raw_sha256"] or digest(normalized) != manifest["normalized_sha256"]:
        raise ValueError("archived research/cache source hashes do not match receipt")
    identifier = manifest.get("snapshot_id")
    if identifier:
        archive.manifest(identifier)
        return identifier
    exchange_timezone = json.loads(raw)["chart"]["result"][0]["meta"]["exchangeTimezoneName"]
    return archive.capture(raw, normalized, {
        "symbol": symbol, "provider": manifest["provider"], "frequency": manifest["frequency"],
        "received_at": manifest["received_at"], "session": "VIX_daily_context" if symbol == "^VIX" else "US_cash_daily",
        "price_basis": "provider_quote_ohlc_not_adjclose", "timezone": exchange_timezone,
        "availability": manifest["availability"], "license_scope": manifest["license_scope"],
        "import_note": "imported historical canonical parsed JSON; original wire bytes not retained"})


def reference_check(archive_root, session="2026-11-03"):
    """Bounded public-source checks, not access-control workarounds."""
    import requests
    results = []
    requests_to_make = [
        ("FRED_NASDAQ100", "https://fred.stlouisfed.org/graph/fredgraph.csv",
          {"id": "NASDAQ100", "cosd": session, "coed": session}),
        ("Nasdaq_public_index_history", "https://api.nasdaq.com/api/index/NDX/historical",
          {"fromdate": datetime.fromisoformat(session).strftime("%m/%d/%Y"), "todate": datetime.fromisoformat(session).strftime("%m/%d/%Y"), "limit": 5}),
    ]
    for provider, url, params in requests_to_make:
        result = {"provider": provider, "url": url, "requested_session": session,
                  "status": "UNVERIFIED", "independent_upstream_confirmed": False}
        try:
            response = requests.get(url, params=params, timeout=25,
                                    headers={"User-Agent": "NocturneResearch/0.1"})
            checksum = digest(response.content)
            from nocturne.adapters.snapshots import immutable_write
            immutable_write(archive_root / "reference-responses" / checksum, response.content)
            result.update(http_status=response.status_code, raw_sha256=checksum,
                          received_at=datetime.now(timezone.utc).isoformat())
            if response.status_code != 200:
                result["status"] = "ACCESS_BLOCKED_OR_UNAVAILABLE"
            elif provider == "FRED_NASDAQ100":
                import io
                import pandas as pd
                frame = pd.read_csv(io.BytesIO(response.content))
                row = frame[frame.iloc[:, 0].astype(str) == session]
                if not row.empty:
                    value = float(row.iloc[0, 1])
                    result.update(status="CURRENT_CLOSE_OBSERVED", close=value,
                                  limitation="Nasdaq-origin series via independent distributor; current vintage, close only, not historical receipt proof")
            else:
                data = response.json().get("data") or {}
                result["response_data"] = data
                result["status"] = "RESPONSE_RECEIVED_REQUIRES_SEMANTIC_REVIEW"
        except Exception as exc:
            result["error_type"] = type(exc).__name__
        results.append(result)
    return results


def main():
    store = ShadowStore(ROOT / "data/shadow/ndx_range")
    before = store.forecast_path.read_bytes()
    forecast = next(f for f in store.forecasts() if f["forecast_id"] == "20d48fc41c2cc0f5c0ae4f2d")
    archive = SnapshotStore(MARKET / "snapshots")
    identifiers = {role: import_existing(ROOT / "data/history/yahoo_daily", symbol, archive)
                   for role, symbol in (("index", "^NDX"), ("vix", "^VIX"))}
    original = verify_issuance(forecast, archive, identifiers)["index"]
    current_id = import_existing(MARKET, "^NDX", archive)
    current = archive.frame(current_id)
    row = current[current.date == forecast["data_date"]].iloc[0]
    record = {"forecast_id": forecast["forecast_id"], "forecast_sha256": digest(canonical(forecast)),
              "issuance_snapshot_ids": identifiers, "revised_snapshot_id": current_id,
              "revised_reference_close": float(row.close),
              "classification": "VERIFIED_AS_ISSUED_PROVIDER_REVISION",
              "recorded_at": datetime.now(timezone.utc).isoformat(),
              "policy": "score original denominator and issued quantiles; never replace forecast",
              "root_cause": "upstream OHLCV payload revision; provider's internal reason unconfirmed",
              "exchange_finality_confirmed": False, "trading_decision": "NO_TRADE"}
    verify_reconciliation(forecast, record, archive, float(row.close))
    stored = store.append_reconciliation(record)
    changes = compare_daily(original, current)
    relevant = [item for item in changes["changed_observations"] if item["date"] == forecast["data_date"]]
    def raw_details(identifier):
        m = archive.manifest(identifier)
        r = json.loads(archive.read_object(m["raw_sha256"]))["chart"]["result"][0]
        return {"source": m["source"], "raw_sha256": m["raw_sha256"], "normalized_sha256": m["normalized_sha256"],
                "exchange_bar_timestamp": r["timestamp"][-1],
                "metadata": {key: r["meta"].get(key) for key in ("symbol", "instrumentType", "exchangeTimezoneName", "dataGranularity", "priceHint", "regularMarketTime")},
                "last_quote_close": r["indicators"]["quote"][0]["close"][-1],
                "last_adjclose": r["indicators"].get("adjclose", [{}])[0].get("adjclose", [None])[-1],
                "corporate_event_types": sorted(r.get("events", {}))}
    report = {"generated_at": record["recorded_at"], "reconciliation": stored,
              "original_journal_sha256": digest(before), "original_forecast_byte_identical": before == store.forecast_path.read_bytes(),
              "reference_session_changes": relevant, "changed_historical_observations": len(changes["changed_observations"]),
              "original_source": raw_details(identifiers["index"]), "revised_source": raw_details(current_id),
              "source_checks": reference_check(MARKET / "snapshots"),
              "forward_outcome": "NOT_MATURED", "note": "original source-as-observed verified, not official exchange truth; no future outcome or new accuracy evidence"}
    if not report["original_forecast_byte_identical"]:
        raise ValueError("forecast journal changed during reconciliation")
    (ROOT / "reports/phase3k_reconciliation.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"classification": stored["classification"], "changes": relevant,
                      "source_checks": [{k: r.get(k) for k in ("provider", "status", "close", "http_status")} for r in report["source_checks"]]}))


if __name__ == "__main__":
    main()
