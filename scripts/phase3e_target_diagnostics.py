import json
from pathlib import Path
import pandas as pd
from nocturne.research.target_diagnostics import nested_target_audit, target_timing

ROOT = Path(__file__).resolve().parents[1]


def main():
    frame = pd.read_csv(ROOT / "data/research/NQ_destinations_phase3d.csv")
    result = {"decision": "NO_PROMOTION", "nested": nested_target_audit(frame),
              "timing": {name: target_timing(group) for name, group in frame.groupby("experiment")}}
    (ROOT / "reports/phase3e_target_diagnostics.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result["nested"]))


if __name__ == "__main__":
    main()
