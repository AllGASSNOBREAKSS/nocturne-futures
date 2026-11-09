"""Nocturne Studio: desktop research services (data, indicators, jobs, forecasts).

Everything here reads stored datasets, the existing engines and the job store.
Nothing places orders; every trading decision stays NO_TRADE.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STATE = ROOT / "data/studio"


def atomic_write(path, text):
    """Readers polling a running job never see a partially written file."""
    path = Path(path)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(text, encoding="utf-8")
    import time
    for attempt in range(40):  # Windows refuses replace while a reader holds the file
        try:
            temp.replace(path)
            return
        except PermissionError:
            time.sleep(0.05)
    temp.replace(path)


def read_json(path):
    """Best-effort read of a file another process may be replacing."""
    import json
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
