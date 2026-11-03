"""Inventory existing local history without downloading or modifying it."""
import json
from pathlib import Path

import pandas as pd

from nocturne.adapters.history import bar_quality, checksum

ROOT = Path(__file__).resolve().parents[1]


def main():
    records = []
    for folder in ("market", "studies", "history"):
        for path in sorted((ROOT / "data" / folder).rglob("*.csv")):
            if "raw" in path.parts or ("yahoo_hourly" in path.parts and not path.name.endswith("_60m.csv")):
                continue
            frame = pd.read_csv(path)
            if not ({"close"}.issubset(frame) or {"date", "value"}.issubset(frame)):
                continue
            time = "timestamp" if "timestamp" in frame else "date"
            if time not in frame:
                continue
            dates = pd.to_datetime(frame[time], utc=True, errors="coerce")
            item = {"path": path.relative_to(ROOT).as_posix(), "rows": len(frame),
                    "sha256": checksum(path), "first": str(dates.min()), "last": str(dates.max()),
                    "span_years": round((dates.max() - dates.min()).total_seconds() / (365.25 * 86400), 3),
                    "frequency": "5min" if "_5m" in path.name else "1h" if "_60m" in path.name else "daily",
                    "source": "existing_repository_cache", "price_basis": "unverified",
                    "point_in_time_vintages": False}
            if "available_at" in frame:
                item["quality"] = bar_quality(frame, item["frequency"])
                if "yahoo_hourly" in path.parts:
                    item["source"] = "yahoo_public_unofficial"
            else:
                value = "close" if "close" in frame else "value"
                item["missing_values"] = int(frame[value].isna().sum())
                if value == "value":
                    item["frequency"] = "monthly" if path.name.startswith(("CPIAUCSL", "UNRATE")) else "daily"
                    item["source"] = "official_FRED_latest_vintage"
                    item["historical_feature_eligible"] = False
            meta_path = path.with_suffix(".meta.json")
            if meta_path.exists():
                metadata = json.loads(meta_path.read_text())
                item["source"] = metadata.get("source", item["source"])
                item["manifest_sha256_matches"] = metadata.get("sha256") == item["sha256"]
            records.append(item)
    report = {"datasets": records, "licensed_intraday_expansion": "DATA_BLOCKED",
              "public_hourly_expansion": "AVAILABLE_SEPARATE_FROM_5MIN_SESSIONS",
              "provider_requirement": "authorized NQ/ES contract-level intraday export or authenticated provider",
              "holdout": "existing cache already examined in Phase 3B; no untouched final period"}
    destination = ROOT / "reports" / "phase3d_history_inventory.json"
    destination.write_text(json.dumps(report, indent=2, default=bool) + "\n")
    print(json.dumps({"datasets": len(records), "report": str(destination)}))


if __name__ == "__main__":
    main()
