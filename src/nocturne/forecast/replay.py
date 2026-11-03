"""Auditable retrospective replay. Never writes the operational forecast journal."""
import hashlib
import json
from pathlib import Path

import pandas as pd

from .v1 import build_forecast_from_bars
from .bundle import build_bundle_from_bars
from .evaluation import evaluate_forecast, evaluate_bundle

REPLAY_VERSION = "phase3e-replay-v1"


def frame_digest(frame):
    return hashlib.sha256(frame.to_csv(index=False, lineterminator="\n").encode()).hexdigest()


def replay_at(bars, spec, asof, *, calendar=None, include_bundle=True):
    frame = bars.copy()
    for col in ("timestamp", "available_at"):
        frame[col] = pd.to_datetime(frame[col], utc=True)
    frame = frame.sort_values("timestamp").reset_index(drop=True)
    asof = pd.Timestamp(asof)
    if asof.tzinfo is None:
        raise ValueError("timezone-aware replay timestamp required")
    known = frame[frame.available_at <= asof].copy()
    if known.empty or known.timestamp.duplicated().any():
        raise ValueError("empty or duplicate replay input")
    # Only the prefix crosses the forecasting boundary; future bars are used
    # exclusively after both forecasts are frozen.
    forecast = build_forecast_from_bars(known, spec, asof.to_pydatetime(), calendar=calendar)
    bundle = build_bundle_from_bars(known, spec, asof.to_pydatetime(), calendar=calendar) if include_bundle else None
    prefix_hash = frame_digest(known)
    identity = f"{REPLAY_VERSION}|{spec.instrument_id}|{asof.isoformat()}|{prefix_hash}"
    frozen = {"replay_id": hashlib.sha256(identity.encode()).hexdigest()[:24],
              "mode": "retrospective_replay", "version": REPLAY_VERSION,
              "asof": asof.isoformat(), "instrument": spec.instrument_id,
              "input_sha256": prefix_hash, "known_rows": len(known),
              "last_available_at": known.available_at.max().isoformat(),
              "forecast": forecast.model_dump(mode="json"),
              "bundle": bundle.model_dump(mode="json") if bundle else None,
              "limitations": ["bar-end availability proxy; historical corrections unknown",
                              "not live shadow or actual execution", "no validated strategy/model inference"]}
    outcome = {"replay_id": frozen["replay_id"], "evaluation_input_sha256": frame_digest(frame),
               "v1": evaluate_forecast(forecast, frame).to_dict(),
               "bundle": evaluate_bundle(bundle, frame) if bundle else None}
    return frozen, outcome


def save_replay(root, frozen, outcome):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    destination = root / f"{frozen['replay_id']}.json"
    content = json.dumps(frozen, sort_keys=True, indent=2, allow_nan=False) + "\n"
    if destination.exists() and destination.read_text(encoding="utf-8") != content:
        raise ValueError("immutable forecast conflict: increment replay version")
    if not destination.exists():
        destination.write_text(content, encoding="utf-8", newline="\n")
    # Evaluation is a separate versioned record; never overwrite a forecast.
    digest = outcome["evaluation_input_sha256"][:16]
    (root / f"{frozen['replay_id']}.outcome.{digest}.json").write_text(
        json.dumps(outcome, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8", newline="\n")
