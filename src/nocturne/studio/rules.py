"""User-defined rule strategies evaluated on causal indicators.

A condition is {"left": ref, "op": op, "right": ref|number}; a ref is
{"indicator": name, "params": {...}}. All conditions must hold at a bar close;
the engine enters at the next bar open, so no rule sees its trade bar.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from ..strategies.base import Signal, TargetSpec
from .indicators import CATALOG, atr, compute

OPS = (">", "<", ">=", "<=", "crosses_above", "crosses_below")
SESSIONS = ("RTH", "ETH", "ASIA", "LONDON", "NEW_YORK")


def validate(config):
    errors = []
    if config.get("side") not in ("LONG", "SHORT"):
        errors.append("side must be LONG or SHORT")
    conditions = config.get("conditions") or []
    if not 1 <= len(conditions) <= 8:
        errors.append("between 1 and 8 conditions are required")
    for i, c in enumerate(conditions):
        if c.get("op") not in OPS:
            errors.append(f"condition {i + 1}: unsupported operator")
        for side in ("left", "right"):
            ref = c.get(side)
            if isinstance(ref, (int, float)) and side == "right":
                continue
            if not isinstance(ref, dict) or ref.get("indicator") not in CATALOG:
                errors.append(f"condition {i + 1}: unknown {side} indicator")
    stop = config.get("stop", {})
    if stop.get("type") not in ("atr", "points") or not 0 < float(stop.get("value", 0)) <= 2000:
        errors.append("stop must be atr multiple or points (0, 2000]")
    targets = config.get("targets_r") or []
    if not 1 <= len(targets) <= 3 or any(not 0.25 <= float(t) <= 20 for t in targets) or list(targets) != sorted(targets):
        errors.append("1-3 ascending target R multiples in [0.25, 20]")
    if not 1 <= int(config.get("horizon_bars", 0)) <= 2000:
        errors.append("horizon_bars must be 1-2000")
    if config.get("session", "RTH") not in SESSIONS:
        errors.append("unsupported session filter")
    if not 1 <= int(config.get("max_trades_per_session", 1)) <= 20:
        errors.append("max_trades_per_session must be 1-20")
    return errors


def _series(frame, ref):
    if isinstance(ref, (int, float)):
        return pd.Series(float(ref), index=frame.index)
    return compute(frame, ref["indicator"], ref.get("params"))


def session_mask(frame, session):
    et = frame.timestamp.dt.tz_convert("America/New_York")
    minutes = et.dt.hour * 60 + et.dt.minute
    windows = {"RTH": (570, 960), "ASIA": (1080, 180), "LONDON": (180, 540), "NEW_YORK": (540, 960), "ETH": (0, 1440)}
    start, end = windows[session]
    return (minutes >= start) | (minutes < end) if start > end else (minutes >= start) & (minutes < end)


@dataclass
class RuleStrategy:
    config: dict
    strategy_id: str = "user_rule"
    version: str = "1"

    def signals(self, frame, spec):
        errors = validate(self.config)
        if errors:
            raise ValueError("; ".join(errors))
        frame = frame.reset_index(drop=True)
        ok = pd.Series(True, index=frame.index)
        for c in self.config["conditions"]:
            left, right = _series(frame, c["left"]), _series(frame, c["right"])
            op = c["op"]
            if op == "crosses_above":
                hit = (left > right) & (left.shift(1) <= right.shift(1))
            elif op == "crosses_below":
                hit = (left < right) & (left.shift(1) >= right.shift(1))
            else:
                hit = {">": left > right, "<": left < right, ">=": left >= right, "<=": left <= right}[op]
            ok &= hit.fillna(False)
        ok &= session_mask(frame, self.config.get("session", "RTH"))
        vol = atr(frame, 14)
        from .indicators import globex_session
        sessions = globex_session(frame.timestamp)
        counts, out = {}, []
        side = self.config["side"]
        sign = 1 if side == "LONG" else -1
        for i in np.flatnonzero(ok.to_numpy())[:-1]:
            day = sessions.iloc[i]
            if counts.get(day, 0) >= int(self.config.get("max_trades_per_session", 1)):
                continue
            ref = float(frame.close.iloc[i])
            stop_cfg = self.config["stop"]
            risk = float(stop_cfg["value"]) * float(vol.iloc[i]) if stop_cfg["type"] == "atr" else float(stop_cfg["value"])
            if not np.isfinite(risk) or risk < spec.tick_size:
                continue
            risk = round(risk / spec.tick_size) * spec.tick_size
            targets = tuple(TargetSpec(f"TP{k + 1}", round(ref + sign * r * risk, 2), float(r)) for k, r in enumerate(self.config["targets_r"]))
            asof = frame.timestamp.iloc[i] + (frame.timestamp.iloc[i + 1] - frame.timestamp.iloc[i])
            try:
                signal = Signal(self.strategy_id, self.version, spec.instrument_id, asof.to_pydatetime(), side, ref, ref,
                                round(ref - sign * risk, 2), targets, int(self.config["horizon_bars"]),
                                ("USER_RULE",), metadata={"bar_index": int(i)})
            except ValueError:
                continue
            counts[day] = counts.get(day, 0) + 1
            out.append((day, signal))
        return out
