import hashlib
import json
from pathlib import Path

root = Path("data/history/yahoo_daily")
problems = []
manifests = sorted((root / "manifests").glob("*.json"))
for manifest in manifests:
    meta = json.loads(manifest.read_text())
    candidates = list((root / "raw").glob("*" + meta["raw_sha256"] + "*"))
    if len(candidates) != 1:
        problems.append((manifest.name, "raw_count", len(candidates)))
    elif hashlib.sha256(candidates[0].read_bytes()).hexdigest() != meta["raw_sha256"]:
        problems.append((manifest.name, "raw_hash"))
    name = meta["symbol"].replace("^", "IDX_").replace("=", "_")
    normalized = root / "normalized" / f"{name}.csv"
    if not normalized.exists():
        problems.append((manifest.name, "missing_normalized"))
    elif hashlib.sha256(normalized.read_bytes()).hexdigest() != meta["normalized_sha256"]:
        problems.append((manifest.name, "normalized_hash"))
print({"manifests": len(manifests), "problems": problems})
