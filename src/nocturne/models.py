"""Typed models for a Nocturne call artifact."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Level:
    r2: float
    r1: float
    pivot: float
    s1: float
    s2: float


@dataclass(frozen=True)
class Instrument:
    code: str
    symbol: str
    name: str
    contract: str
    tick: float
    multiplier: float
    last: float
    prior_close: float
    rth_open: float
    rth_high: float
    rth_low: float
    rth_close: float
    vwap: float
    overnight_high: float
    overnight_low: float
    atr14: float
    sma20: float
    sma50: float
    sma200: float
    high_52w: float
    low_52w: float
    vol20: float


@dataclass(frozen=True)
class Scenario:
    name: str
    label: str
    probability: float
    closes: dict[str, tuple[float, float]]


@dataclass(frozen=True)
class Call:
    call_id: str
    session: str
    published_at: str
    engine: str
    macro: dict[str, Any]
    instruments: dict[str, Instrument]
    bias: dict[str, str]
    confidence: dict[str, float]
    predicted_close: dict[str, tuple[float, float]]
    predicted_range: dict[str, tuple[float, float]]
    sigma_close: dict[str, tuple[float, float]]
    levels: dict[str, Level]
    scenarios: tuple[Scenario, ...]
    sources: tuple[str, ...]

    @classmethod
    def load(cls, path: str | Path) -> "Call":
        return cls.from_dict(json.loads(Path(path).read_text(encoding="utf-8")))

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Call":
        instruments = {
            code: Instrument(code=code, **data)
            for code, data in raw["instruments"].items()
        }
        scenarios = tuple(
            Scenario(
                name=s["name"],
                label=s["label"],
                probability=float(s["probability"]),
                closes={k: (float(v[0]), float(v[1])) for k, v in s["closes"].items()},
            )
            for s in raw["scenarios"]
        )
        total = sum(s.probability for s in scenarios)
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"scenario probabilities must sum to 1.0, got {total:.6f}")

        return cls(
            call_id=raw["call_id"],
            session=raw["session"],
            published_at=raw["published_at"],
            engine=raw.get("engine", "nocturne"),
            macro=raw.get("macro", {}),
            instruments=instruments,
            bias=raw["bias"],
            confidence={k: float(v) for k, v in raw["confidence"].items()},
            predicted_close={k: (float(v[0]), float(v[1])) for k, v in raw["predicted_close"].items()},
            predicted_range={k: (float(v[0]), float(v[1])) for k, v in raw["predicted_range"].items()},
            sigma_close={
                k: (float(v[0]), float(v[1]))
                for k, v in raw.get(
                    "sigma_close",
                    {code: (0.0, 0.0) for code in raw["instruments"]},
                ).items()
            },
            levels={k: Level(**v) for k, v in raw["levels"].items()},
            scenarios=scenarios,
            sources=tuple(raw.get("sources", [])),
        )

    def sigma_close_point(self, code: str) -> float:
        inst = self.instruments[code]
        return inst.last * (inst.vol20 / 100.0) / (252 ** 0.5)
