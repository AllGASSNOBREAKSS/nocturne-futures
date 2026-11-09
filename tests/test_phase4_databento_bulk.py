"""Credit guards for Databento acquisition: caps, no double charge, reuse, validation."""
import io
import json

import pandas as pd
import pytest


zstandard = pytest.importorskip("zstandard")  # optional; not in the hash-locked runtime
from nocturne.adapters.databento_bulk import Acquirer, CreditGuard, read_chunk, validate_ohlcv

CSV = ("ts_event,rtype,publisher_id,instrument_id,open,high,low,close,volume,symbol\n"
       "2026-11-02T14:30:00Z,33,1,42,27000.25,27010.00,26995.50,27005.75,120,NQ.v.0\n"
       "2026-11-02T14:31:00Z,33,1,42,27005.75,27012.25,27001.00,27011.00,95,NQ.v.0\n").encode()


class Response:
    def __init__(self, status=200, text="", body=b""):
        self.status_code, self.text, self.body = status, text, body

    def iter_content(self, size):
        yield self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeProvider:
    def __init__(self, cost="1.50", fail_download=False):
        self.cost, self.fail, self.downloads = cost, fail_download, 0

    def get(self, url, params=None, auth=None, timeout=None, stream=False):
        method = url.rsplit("/", 1)[-1]
        if method == "metadata.get_cost":
            return Response(text=self.cost)
        if method == "metadata.get_billable_size":
            return Response(text="1000")
        if method == "metadata.get_record_count":
            return Response(text="2")
        self.downloads += 1
        if self.fail:
            return Response(status=500)
        return Response(body=zstandard.ZstdCompressor().compress(CSV))


PARAMS = {"dataset": "GLBX.MDP3", "symbols": "NQ.v.0", "stype_in": "continuous", "schema": "ohlcv-1m", "start": "2026-11-02", "end": "2026-11-03"}


def test_completed_chunks_are_reused_not_rebought(tmp_path):
    provider = FakeProvider()
    acq = Acquirer(tmp_path, 10, 125, key="k", session=provider)
    first = acq.chunk("c1", PARAMS)
    again = Acquirer(tmp_path, 10, 125, key="k", session=provider).chunk("c1", PARAMS)
    assert provider.downloads == 1 and again["reused"] and first["raw_sha256"] == again["raw_sha256"]
    frame = read_chunk(tmp_path / first["raw_file"])
    clean, report = validate_ohlcv(frame)
    assert report["off_tick_prices"] == 0 and report["duplicates"] == 0 and len(clean) == 2


def test_run_cap_and_ceiling_block_before_any_download(tmp_path):
    provider = FakeProvider(cost="6.00")
    acq = Acquirer(tmp_path, 10, 125, key="k", session=provider)
    acq.chunk("a", PARAMS)
    with pytest.raises(CreditGuard, match="run cap"):
        acq.chunk("b", PARAMS)
    assert provider.downloads == 1
    with pytest.raises(CreditGuard, match="ceiling"):
        Acquirer(tmp_path, 1000, 10, key="k", session=provider).chunk("c", PARAMS)
    assert provider.downloads == 1


def test_uncertain_reservation_is_never_retried(tmp_path):
    failing = FakeProvider(fail_download=True)
    with pytest.raises(CreditGuard):
        Acquirer(tmp_path, 10, 125, key="k", session=failing).chunk("x", PARAMS)
    healthy = FakeProvider()
    with pytest.raises(CreditGuard, match="never auto-retried"):
        Acquirer(tmp_path, 10, 125, key="k", session=healthy).chunk("x", PARAMS)
    assert healthy.downloads == 0
    # The uncertain attempt still counts against the ceiling.
    assert float(Acquirer(tmp_path, 10, 125, key="k", session=healthy).committed()) == pytest.approx(1.5)


def test_tampered_chunk_is_detected(tmp_path):
    acq = Acquirer(tmp_path, 10, 125, key="k", session=FakeProvider())
    record = acq.chunk("t", PARAMS)
    (tmp_path / record["raw_file"]).write_bytes(b"tampered")
    with pytest.raises(CreditGuard, match="checksum"):
        Acquirer(tmp_path, 10, 125, key="k", session=FakeProvider()).chunk("t", PARAMS)


def test_missing_key_refuses():
    with pytest.raises(CreditGuard):
        Acquirer("unused", 1, 1, key="", session=FakeProvider())


def test_validator_flags_structural_problems():
    frame = pd.read_csv(io.BytesIO(CSV))
    bad = pd.concat([frame, frame.iloc[[0]].assign(high=26000.10)], ignore_index=True)
    clean, report = validate_ohlcv(bad)
    assert report["duplicates"] == 1 and report["off_tick_prices"] >= 1
    assert len(clean) == 2
