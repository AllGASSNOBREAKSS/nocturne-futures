import copy
import hashlib
import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from nocturne.adapters.snapshots import SnapshotStore, canonical, digest, immutable_write
from nocturne.adapters.yahoo_history import _frame, fetch_daily_history
from nocturne.adapters.source_comparison import compare_sources, estimate_futures_bar_volume
from nocturne.shadow import ShadowStore, audit_forecasts, generate, load_artifact
from nocturne.shadow.reconciliation import verify_issuance, verify_reconciliation

ROOT = Path(__file__).resolve().parents[1]


def payload(symbol="^NDX", revision=False):
    dates = pd.bdate_range("2024-01-02", periods=320, tz="UTC")
    closes = [100. + i for i in range(len(dates))] if symbol == "^NDX" else [20.] * len(dates)
    quote = {"open": closes.copy(), "close": closes.copy(), "high": [x + 1 for x in closes],
             "low": [x - 1 for x in closes], "volume": [1000] * len(dates)}
    if revision:
        for key in ("open", "high", "low", "close"):
            quote[key][-1] += .25
        quote["volume"][-1] = 2000
    return {"chart": {"result": [{"meta": {"symbol": symbol, "dataGranularity": "1d", "instrumentType": "INDEX", "exchangeTimezoneName": "America/Chicago" if symbol == "^VIX" else "America/New_York"},
                                  "timestamp": [int(x.timestamp()) for x in dates], "indicators": {"quote": [quote]}}]}}


def capture(store, symbol="^NDX", revision=False, received="2025-03-25T00:30:00+00:00"):
    value = payload(symbol, revision)
    raw = canonical(value)
    normalized = _frame(value, symbol).to_csv(index=False).encode()
    source = {"symbol": symbol, "provider": "yahoo_public_unofficial", "frequency": "1d",
              "received_at": received, "session": "VIX_daily_context" if symbol == "^VIX" else "US_cash_daily", "timezone": "America/Chicago" if symbol == "^VIX" else "America/New_York",
              "price_basis": "provider_quote_ohlc_not_adjclose"}
    return store.capture(raw, normalized, source, wire=b" \n" + raw)


def evidence(tmp_path):
    archive = SnapshotStore(tmp_path / "archive")
    ids = {"index": capture(archive), "vix": capture(archive, "^VIX")}
    store = ShadowStore(tmp_path / "shadow")
    artifact = load_artifact(ROOT / "models/shadow", "ndx-range-v1")
    now = pd.Timestamp("2025-03-25T01:00:00Z").to_pydatetime()
    generated = generate(artifact, store, archive.frame(ids["index"]), archive.frame(ids["vix"]), now,
                         "RESEARCH_VALIDATED_PENDING_SHADOW", source={"snapshot_ids": ids})
    assert generated["status"] == "STORED"
    return archive, store, ids, store.latest()


def test_exact_wire_and_normalized_archive_tamper_detection(tmp_path):
    archive = SnapshotStore(tmp_path)
    identifier = capture(archive)
    manifest = archive.manifest(identifier)
    assert archive.read_object(manifest["wire_sha256"]).startswith(b" \n")
    assert len(archive.frame(identifier)) == 320
    object_path = archive._object(manifest["raw_sha256"])
    object_path.write_bytes(b"corrupted fixture")
    with pytest.raises(ValueError, match="checksum"):
        archive.manifest(identifier)


def test_revisions_do_not_replace_original_objects_and_old_import_cannot_regress_head(tmp_path):
    archive = SnapshotStore(tmp_path)
    first = capture(archive)
    before = archive.read_object(archive.manifest(first)["normalized_sha256"])
    revised = capture(archive, revision=True, received="2025-03-25T02:00:00Z")
    capture(archive)  # importing old evidence is not a new live revision
    rows = [json.loads(line) for line in (tmp_path / "revisions.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["previous_snapshot_id"] == first
    assert rows[0]["snapshot_id"] == revised
    assert set(rows[0]["changed_observations"][-1]["fields"]) == {"open", "high", "low", "close", "volume"}
    assert archive.read_object(archive.manifest(first)["normalized_sha256"]) == before
    head = json.loads(next((tmp_path / "heads").glob("*.json")).read_text())
    assert head["snapshot_id"] == revised


def test_reconciliation_replays_issuance_and_retains_original_denominator(tmp_path):
    archive, store, ids, forecast = evidence(tmp_path)
    original_bytes = store.forecast_path.read_bytes()
    revised = capture(archive, revision=True, received="2025-03-25T02:00:00Z")
    current = archive.frame(revised)
    close = float(current.close.iloc[-1])
    assert audit_forecasts(store, current, snapshot_root=archive.root)["failed"]
    record = {"forecast_id": forecast["forecast_id"], "forecast_sha256": digest(canonical(forecast)),
              "issuance_snapshot_ids": ids, "revised_snapshot_id": revised,
              "revised_reference_close": close, "classification": "VERIFIED_AS_ISSUED_PROVIDER_REVISION"}
    assert verify_reconciliation(forecast, record, archive, close)
    store.append_reconciliation(record)
    store.append_reconciliation(record)
    assert len(store.reconciliations()) == 1
    audit = audit_forecasts(store, current, snapshot_root=archive.root)
    assert audit["failed"] == []
    assert store.forecast_path.read_bytes() == original_bytes
    assert store.latest()["reference_close"] != close
    modified = copy.deepcopy(forecast)
    modified["quantiles"]["p90"] += .01
    with pytest.raises(ValueError, match="bind"):
        verify_reconciliation(modified, record, archive, close)


def test_issuance_snapshot_receipt_after_forecast_fails_closed(tmp_path):
    archive, _, ids, forecast = evidence(tmp_path)
    ids["index"] = capture(archive, received="2025-03-25T02:00:00Z")
    with pytest.raises(ValueError, match="chronology"):
        verify_issuance(forecast, archive, ids)


def test_legacy_windows_input_digest_replays_without_changing_values(tmp_path):
    from dataclasses import replace
    from nocturne.shadow.features import MIN_HISTORY, build_features
    archive, _, ids, forecast = evidence(tmp_path)
    index, vix = archive.frame(ids["index"]), archive.frame(ids["vix"])
    index["date"] = pd.to_datetime(index.date)
    legacy_hash = digest(index.tail(MIN_HISTORY)[["date", "close", "high", "low", "volume"]].to_csv(index=False, lineterminator="\r\n").encode())
    replay = replace(build_features(index, vix, forecast["created_at"]), dataset_sha256=legacy_hash)
    legacy = {**forecast, "dataset_sha256": legacy_hash, "feature_digest": replay.digest()}
    legacy.pop("dataset_digest_format")
    legacy.pop("record_sha256")
    verify_issuance(legacy, archive, ids)


def test_raw_normalization_and_identity_mismatch_rejected(tmp_path):
    archive = SnapshotStore(tmp_path)
    raw = canonical(payload())
    frame = _frame(payload(), "^NDX")
    frame.loc[0, "close"] += .5
    source = {"symbol": "^NDX", "frequency": "1d", "received_at": "2025-03-25T00:00:00Z"}
    with pytest.raises(ValueError, match="close disagree"):
        archive.capture(raw, frame.to_csv(index=False).encode(), source)
    with pytest.raises(ValueError, match="identity"):
        archive.capture(raw, _frame(payload(), "^NDX").to_csv(index=False).encode(), {**source, "symbol": "QQQ"})


def test_conflicting_same_receipt_is_not_a_valid_revision(tmp_path):
    archive = SnapshotStore(tmp_path)
    capture(archive)
    with pytest.raises(ValueError, match="same receipt"):
        capture(archive, revision=True)


def test_immutable_writes_and_frozen_research_fetch(tmp_path, monkeypatch):
    path = tmp_path / "object"
    immutable_write(path, b"original")
    with pytest.raises(ValueError, match="immutable"):
        immutable_write(path, b"replacement")
    (tmp_path / "FROZEN").write_text("fixture")
    monkeypatch.setattr("nocturne.adapters.yahoo_history._fetch_daily", lambda *a, **k: pytest.fail("must not fetch frozen research"))
    with pytest.raises(ValueError, match="frozen"):
        fetch_daily_history("^NDX", tmp_path)


def test_frozen_artifact_mutation_rejected_before_unpickle(tmp_path):
    target = tmp_path / "ndx-range-v1"
    shutil.copytree(ROOT / "models/shadow/ndx-range-v1", target)
    (target / "model.joblib").write_bytes(b"changed fixture")
    with pytest.raises(ValueError, match="checksum"):
        load_artifact(tmp_path, "ndx-range-v1")


def test_original_forecast_line_remains_byte_identical():
    original_line = (ROOT / "data/shadow/ndx_range/forecasts.jsonl").read_bytes().splitlines(keepends=True)[0]
    assert hashlib.sha256(original_line).hexdigest() == "61f4034a108ccf6545959d4dac39e18ae3c5247ae4557dddf9e9a8158113a1b3"


def test_equivalent_source_comparison_never_substitutes_an_etf_for_an_index():
    frame = pd.DataFrame({"date": ["2026-11-03"], "close": [100.]})
    contract = {"instrument": "^NDX", "kind": "index", "session": "cash", "timezone": "America/New_York",
                "price_basis": "quote_ohlc", "currency": "USD", "frequency": "1d"}
    with pytest.raises(ValueError, match="incomparable"):
        compare_sources(frame, frame, contract, {**contract, "instrument": "QQQ"}, {"close": .005})
    revised = frame.copy()
    revised["close"] += .1
    assert compare_sources(frame, revised, contract, contract, {"close": .005})["status"] == "UNRESOLVED_CONFLICT"
    with pytest.raises(ValueError, match="tolerances"):
        compare_sources(frame, frame, contract, contract, {})
    assert estimate_futures_bar_volume()["one_minute_rows"] == 695520
