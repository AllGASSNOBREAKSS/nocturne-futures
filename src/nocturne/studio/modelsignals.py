"""Trade signals generated from the models' out-of-sample predictions.

Every probability used here comes from a walk-forward fit that never saw the session it
scores (levelmodel.study / predictor.track_record), so backtests of these signals are not
in-sample. Entries are at the open of the first 5m bar after the cutoff.

- ml_levels: at the cutoff, the open level with the highest touch probability that is at
  least `min_distance_atr` away; target = the level, stop = distance / RR.
- ml_direction: next-session direction model at 09:30 ET; long if p_up >= threshold,
  short if p_up <= 1 - threshold. Stop = ATR multiple, targets = RR x risk.
- session_trend: at the cutoff, long when price is above VWAP and above the 30-minute
  opening range, short when below both (fade=True inverts). Stop/targets as above.
"""
from __future__ import annotations

import pandas as pd

from ..strategies.base import Signal, TargetSpec
from . import dataset, levelmodel, predictor, sessions

KINDS = {
    "ml_levels": {"label": "ML level targets", "params": {"cutoff": list(sessions.CUTOFFS), "min_probability": [0.3, 0.97, 0.6],
                                                          "min_distance_atr": [0.05, 2.0, 0.25], "side": ["BOTH", "LONG", "SHORT"]}},
    "ml_direction": {"label": "ML next-session direction", "params": {"threshold": [0.5, 0.8, 0.55], "side": ["BOTH", "LONG", "SHORT"]}},
    "session_trend": {"label": "VWAP + opening-range trend", "params": {"cutoff": ["post_ib", "midday", "afternoon"], "fade": [False, True],
                                                                     "side": ["BOTH", "LONG", "SHORT"]}},
}


def validate(kind, params, exit_cfg):
    errors = []
    spec = KINDS[kind]["params"]
    for key, value in (params or {}).items():
        bounds = spec.get(key)
        if bounds is None:
            errors.append(f"unknown parameter {key}")
        elif isinstance(bounds[0], str) or isinstance(bounds[0], bool):
            if value not in bounds:
                errors.append(f"{key} must be one of {bounds}")
        elif not bounds[0] <= float(value) <= bounds[1]:
            errors.append(f"{key} must be in [{bounds[0]}, {bounds[1]}]")
    stop = (exit_cfg or {}).get("stop")
    if kind != "ml_levels" and stop and stop.get("type") not in ("atr", "points"):
        errors.append("stop type must be atr or points")
    return errors


def _param(kind, params, key):
    value = (params or {}).get(key)
    if value is None:
        bounds = KINDS[kind]["params"][key]
        value = bounds[0] if isinstance(bounds[0], (str, bool)) else bounds[2]
    return value


def _asof(day, minute):
    return pd.Timestamp(f"{day} {minute // 60:02d}:{minute % 60:02d}", tz=sessions.ET).tz_convert("UTC")


def _horizon(minute):
    return max(1, (sessions.NY_CLOSE - minute) // 5 - 1)


def _rr(exit_cfg):
    rr = [float(r) for r in ((exit_cfg or {}).get("rr") or [1.0])]
    return sorted(rr)


def _risk(exit_cfg, atr):
    stop = (exit_cfg or {}).get("stop") or {"type": "atr", "value": 0.25}
    return float(stop["value"]) * atr if stop["type"] == "atr" else float(stop["value"])


def _make(kind, root, day, minute, side, ref, risk, targets, reason, meta):
    sign = 1 if side == "LONG" else -1
    return Signal(strategy_id=f"model:{kind}", strategy_version="1", instrument_id=root, asof=_asof(day, minute).to_pydatetime(),
                  side=side, entry_low=ref, entry_high=ref, stop=round(ref - sign * risk, 2),
                  targets=tuple(TargetSpec(f"TP{i + 1}", round(p, 2), round(abs(p - ref) / risk, 3)) for i, p in enumerate(targets)),
                  horizon_bars=_horizon(minute), reason_codes=(reason,), metadata=meta)


def _daily_atr(root):
    data, _ = dataset.build(root, "databento")
    nxt = data.next_session.astype(str)
    return dict(zip(nxt, data.atr20_pts)), dict(zip(nxt, data.close))


def signals(kind, params, root, exit_cfg, start=None, end=None):
    side_filter = _param(kind, params, "side")
    out = []
    if kind == "ml_levels":
        cutoff = _param(kind, params, "cutoff")
        min_p, min_d = float(_param(kind, params, "min_probability")), float(_param(kind, params, "min_distance_atr"))
        oos = pd.read_csv(levelmodel.oos_path(root)) if levelmodel.oos_path(root).exists() else pd.DataFrame()
        if oos.empty:
            raise ValueError("level model study not built yet")
        c = list(sessions.CUTOFFS).index(cutoff)
        oos = oos[(oos.cutoff == c) & (oos.abs_atr >= min_d) & (oos.p >= min_p)]
        if start:
            oos = oos[oos.session >= str(start)[:10]]
        if end:
            oos = oos[oos.session <= str(end)[:10]]
        rr = _rr(exit_cfg)[0]
        minute = sessions.CUTOFFS[cutoff]
        for day, g in oos.sort_values("p", ascending=False).groupby("session", sort=True):
            for row in g.to_dict("records"):
                side = "LONG" if row["price"] > row["ref"] else "SHORT"
                if side_filter in ("LONG", "SHORT") and side != side_filter:
                    continue
                distance = abs(row["price"] - row["ref"])
                out.append((day, _make(kind, root, day, minute, side, row["ref"], distance / rr, [row["price"]], sessions.LEVEL_NAMES[row["key"]],
                                       {"p": row["p"], "level": row["key"]})))
                break
        return out
    atr, close = _daily_atr(root)
    rr = _rr(exit_cfg)
    if kind == "ml_direction":
        thr = float(_param(kind, params, "threshold"))
        oos = pd.read_csv(predictor.oos_path(root))
        data, _ = dataset.build(root, "databento")
        nxt = dict(zip(data.date.astype(str), data.next_session.astype(str)))
        for row in oos.to_dict("records"):
            day = nxt.get(str(row["date"]))
            if not day or day == "NaT" or (start and day < str(start)[:10]) or (end and day > str(end)[:10]):
                continue
            p = row["p_direction"]
            side = "LONG" if p >= thr else "SHORT" if p <= 1 - thr else None
            if side is None or (side_filter in ("LONG", "SHORT") and side != side_filter):
                continue
            # Reference = prior settle; the engine fills at the 09:30 bar open and skips gaps through TP1.
            ref = float(row["close"])
            risk = _risk(exit_cfg, float(row["atr"]))
            sign = 1 if side == "LONG" else -1
            out.append((day, _make(kind, root, day, sessions.NY_OPEN, side, ref, risk, [ref + sign * r * risk for r in rr], f"p_up={p:.3f}", {"p": p})))
        return out
    if kind == "session_trend":
        cutoff, fade = _param(kind, params, "cutoff"), bool(_param(kind, params, "fade"))
        _, state = levelmodel.build(root)
        state = state[(state.cutoff_name == cutoff) & state.orb.notna()]
        for row in state.to_dict("records"):
            day = str(row["session"])
            if (start and day < str(start)[:10]) or (end and day > str(end)[:10]) or day not in atr:
                continue
            up, dn = row["vs_vwap"] > 0 and row["orb"] == "above", row["vs_vwap"] < 0 and row["orb"] == "below"
            side = ("LONG" if up else "SHORT" if dn else None)
            if side and fade:
                side = "SHORT" if side == "LONG" else "LONG"
            if side is None or (side_filter in ("LONG", "SHORT") and side != side_filter):
                continue
            ref, risk = float(row["price"]), _risk(exit_cfg, float(atr[day]))
            sign = 1 if side == "LONG" else -1
            out.append((day, _make(kind, root, day, sessions.CUTOFFS[cutoff], side, ref, risk, [ref + sign * r * risk for r in rr],
                                   "fade" if fade else "trend", {})))
        return out
    raise ValueError(f"unknown model strategy {kind}")
