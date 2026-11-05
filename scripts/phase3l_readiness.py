"""Concrete access and research gates. No licensed download or purchase."""
import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from nocturne.adapters.registry import registry
from nocturne.adapters.source_comparison import estimate_futures_bar_volume
from nocturne.adapters.snapshots import digest
from nocturne.ml.status import governance
from nocturne.instruments import get_instrument
from nocturne.research.contract_replay import load_contract_receipts

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--probe-context", action="store_true")
    args = parser.parse_args()
    access = {}
    for instrument, contract in (("NQ", "NQZ6"), ("ES", "ESZ6")):
        try:
            history = load_contract_receipts(ROOT / "data/licensed/databento", get_instrument(instrument), contract)
            access[instrument] = {"status": history["status"], "contract": contract,
                                  "rows": len(history["bars"]), "receipt_count": len(history["receipts"])}
        except (ValueError, OSError, KeyError) as exc:
            access[instrument] = {"status": "DATA_BLOCKED", "error_type": type(exc).__name__}
    probes = {}
    if args.probe_context:
        from nocturne.adapters.fred import fetch_context
        from nocturne.adapters.bls import fetch_series, save
        for name, function in (
            ("FRED_DGS10", lambda: fetch_context("DGS10", ROOT / "data/shadow/macro/fred", start="2026-10-01", end="2026-11-04")),
            ("FRED_NASDAQ100", lambda: fetch_context("NASDAQ100", ROOT / "data/shadow/macro/fred", start="2026-11-03", end="2026-11-04")),
            ("BLS_CPI", lambda: save(fetch_series(["CUUR0000SA0"], 2025, 2026), ROOT / "data/shadow/macro/bls")),
        ):
            try:
                result = function()
                snapshot = Path(result["path"]) if result.get("path") else None
                probes[name] = {"status": "RESPONSE_VERIFIED", "rows": result.get("rows"), "pit_feature_eligible": False,
                                "received_at": result.get("received_at", datetime.now(timezone.utc).isoformat()),
                                "snapshot_sha256": result.get("sha256") or (digest(snapshot.read_bytes()) if snapshot else None),
                                "availability": "current-vintage context only; observation date is not publication time"}
                if name == "FRED_NASDAQ100":
                    import pandas as pd
                    frame = pd.read_csv(ROOT / "data/shadow/macro/fred/normalized" / f"NASDAQ100_{result['sha256']}.csv")
                    rows = frame[frame.date.eq("2026-11-04") & frame.value.notna()]
                    if not rows.empty:
                        probes[name]["november_4_close"] = float(rows.value.iloc[0])
                    probes[name]["november_4_observation_status"] = "PRESENT" if not rows.empty else "NOT_PRESENT_IN_CURRENT_RESPONSE"
                    probes[name]["latest_observation_date"] = result.get("last")
                    probes[name]["lineage_warning"] = "separate distributor, shared Nasdaq origin; does not verify high/low, historical availability or exchange finality"
            except Exception as exc:
                probes[name] = {"status": "CONNECTION_OR_ACCESS_BLOCKED", "error_type": type(exc).__name__,
                                "security": "TLS verification and existing network configuration unchanged"}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "credential_presence": {key: bool(os.environ.get(key)) for key in ("DATABENTO_API_KEY", "FRED_API_KEY", "BLS_API_KEY", "NASDAQ_DATA_LINK_API_KEY")},
              "providers": registry(), "raw_contracts": access, "context_probes": probes,
              "data_tiers": {"tier1_bars": "DATA_BLOCKED" if all(v["status"] == "DATA_BLOCKED" for v in access.values()) else "RECEIPTS_REQUIRE_SESSION_AND_PIT_REVIEW",
                             "tier2_trades_quotes": "DATA_BLOCKED_NO_VERIFIED_RECEIPTS", "tier3_depth_mbo": "DATA_BLOCKED_NO_VERIFIED_RECEIPTS"},
              "bounded_pilot": {"dataset": "GLBX.MDP3", "schema": "ohlcv-1m", "stype_in": "raw_symbol",
                                "contracts": ["NQZ6", "ESZ6"], "start": "2026-11-01T23:00:00Z", "end": "2026-11-02T22:00:00Z",
                                "planned_max_minute_rows_both": 2760, "download_attempted": False,
                                "cost_usd": None, "cost_status": "REQUIRES_AUTHENTICATED_PROVIDER_SIZE_COST_QUOTE_AND_ENTITLEMENT; NO_PURCHASE_AUTHORIZED"},
              "minimum_useful_coverage": {"plumbing": "one complete session per explicit contract",
                                          "predictive_research": "recommend 3+ years across explicit contracts/regimes; chronological training, calibration, untouched evaluation and sufficient event counts still required"},
              "storage_planning_not_observations": estimate_futures_bar_volume(),
              "research_gates": {"new_orderflow_directional_ablation": "DATA_BLOCKED", "new_target_survival_fit": "DATA_BLOCKED",
                                 "directional_auc": None, "target_first_probability": None, "session_direction_probability": None},
              "model_governance": governance(),
              "survival_method": {"version": "aj-discrete-v2-event-only-survival", "new_fit": False,
                                  "legacy_aj_v1_status": "INVALID_CENSORING_UPDATE_REQUIRES_RECOMPUTATION"},
              "trading_decision": "NO_TRADE", "purchase_performed": False}
    (ROOT / "reports/phase3l_readiness.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"raw_contracts": access, "context_probes": probes, "paid_download_attempted": False}))


if __name__ == "__main__":
    main()
