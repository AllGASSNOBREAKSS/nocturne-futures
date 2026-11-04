"""Provider and futures-data readiness report for Phase 3I."""
import json
import os
from pathlib import Path

import pandas as pd

from nocturne.adapters.registry import registry
from nocturne.instruments import get_instrument
from nocturne.research.contract_targets import readiness

ROOT = Path(__file__).resolve().parents[1]
TIERS = {
    "tier1_intraday_bars": {
        "requires": ["NQ/ES raw contract_id", "1m and 5m OHLCV", "exchange timestamps",
                     "actual volume", "tick-size alignment", "roll metadata"],
        "provider": "Databento GLBX.MDP3 ohlcv-1m",
        "status": "DATA_BLOCKED",
    },
    "tier2_trades_quotes": {
        "requires": ["trades", "bid/ask quotes", "aggressor side where supported", "volume at price"],
        "provider": "Databento trades / bbo-1s / bbo-1m",
        "status": "DATA_BLOCKED",
    },
    "tier3_order_book": {
        "requires": ["mbp-1 or mbp-10 depth", "mbo where licensed", "sequence integrity"],
        "provider": "Databento mbp / mbo (entitlement dependent)",
        "status": "DATA_BLOCKED",
    },
}


def contract_inventory() -> dict:
    root = ROOT / "data/history/futures"
    candidates = sorted(root.rglob("*.csv")) if root.exists() else []
    frames = []
    for path in candidates:
        try:
            frame = pd.read_csv(path, nrows=5000)
        except Exception:
            continue
        if "contract_id" in frame and frame.contract_id.notna().any():
            frames.append(path)
    if not frames:
        return readiness(None, get_instrument("NQ"))
    frame = pd.read_csv(frames[0])
    return {**readiness(frame, get_instrument("NQ")),
            "files": [str(path.relative_to(ROOT)) for path in frames]}


def main():
    providers = registry()
    report = {
        "generated_at": pd.Timestamp.now(tz="UTC").isoformat(),
        "providers": {item["name"]: {"status": item["status"], "access": item["access"],
                                     "credential_present": item["credential_present"],
                                     "verified_with_real_data": item["verified_with_real_data"]}
                      for item in providers["providers"]},
        "credential_env_present": {name: bool(os.environ.get(name)) for name in
                                   ("DATABENTO_API_KEY", "FRED_API_KEY", "BLS_API_KEY",
                                    "NASDAQ_DATA_LINK_API_KEY")},
        "tiers": TIERS,
        "contract_data": contract_inventory(),
        "free_context": {"daily_manifests": [
            {key: manifest.get(key) for key in ("symbol", "rows", "first", "last", "received_at")}
            for path in sorted((ROOT / "data/history/yahoo_daily/manifests").glob("*.json"))
            for manifest in [json.loads(path.read_text())]],
                         "note": "historical inventory, not current availability; free context cannot substitute for contract-level intraday"},
        "validation_status": "RESEARCH_ONLY",
        "connectivity": "Databento not attempted: credential absent" if not os.environ.get("DATABENTO_API_KEY") else "credential present; entitlement/download not verified",
        "trading_decision": "NO_TRADE",
        "notes": ["no credential values are printed or stored",
                  "fixture-tested adapters are not live integrations",
                  "tier statuses change only after a verified real download"],
    }
    (ROOT / "reports/phase3i_readiness.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"providers": {k: v["status"] for k, v in report["providers"].items()},
                      "contract_data": report["contract_data"]["status"]}, indent=1))


if __name__ == "__main__":
    main()
