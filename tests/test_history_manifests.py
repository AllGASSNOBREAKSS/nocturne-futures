"""Verify frozen provenance survives a Windows/Linux Git checkout."""
import json
from pathlib import Path

from nocturne.adapters.history import checksum

ROOT = Path(__file__).resolve().parents[1]


def test_committed_history_hashes_match_manifests():
    fred = ROOT / "data/history/fred"
    for path in fred.glob("*.json"):
        meta = json.loads(path.read_text())
        name = f"{meta['series']}_{meta['sha256']}.csv"
        assert checksum(fred / "raw" / name) == meta["sha256"]
        assert checksum(fred / "normalized" / name) == meta["normalized_sha256"]
    for path in (ROOT / "data/history/yahoo_hourly").glob("*/manifests/*.json"):
        meta = json.loads(path.read_text())
        root = path.parent.parent
        assert checksum(root / "raw" / f"{meta['raw_sha256']}.csv") == meta["raw_sha256"]
        assert checksum(root / meta["normalized_path"]) == meta["normalized_sha256"]


def test_frozen_research_inputs_match_reports():
    report = json.loads((ROOT / "reports/phase3d_hourly_validation.json").read_text())
    for instrument, entry in report["instruments"].items():
        assert checksum(ROOT / f"data/research/{instrument}_two_hour_phase3d.csv") == entry["dataset_sha256"]
    report = json.loads((ROOT / "reports/phase3d_validation.json").read_text())
    assert checksum(ROOT / "data/research/session_dataset_NQ_phase3d.csv") == report["dataset_sha256"]
