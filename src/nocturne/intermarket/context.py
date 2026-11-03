"""Clock-aligned intermarket context.

VX futures are not available in this environment. `^VIX` spot is used only as a
labelled proxy; it is never called CFE VX. ZN/ZB are Yahoo front-month proxies
until a licensed adapter is connected.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime

import numpy as np
import pandas as pd


@dataclass
class IntermarketState:
    asof: str
    es_return_1d: float | None = None
    nq_return_1d: float | None = None
    relative_1d: float | None = None
    beta_20d: float | None = None
    corr_20d: float | None = None
    spread_z_20d: float | None = None
    vix_level: float | None = None
    vix_change_5d: float | None = None
    vx_futures_available: bool = False
    vix_proxy: str = "NONE"
    zn_return_1d: float | None = None
    zb_return_1d: float | None = None
    dxy_level: float | None = None
    flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _returns(frame: pd.DataFrame) -> pd.Series:
    return frame.set_index("date")["close"].astype(float).pct_change()


def build_intermarket_state(
    es: pd.DataFrame,
    nq: pd.DataFrame,
    vix: pd.DataFrame | None = None,
    zn: pd.DataFrame | None = None,
    zb: pd.DataFrame | None = None,
    dxy: pd.DataFrame | None = None,
    asof: str | None = None,
) -> IntermarketState:
    es_ret = _returns(es)
    nq_ret = _returns(nq)
    aligned = pd.concat({"es": es_ret, "nq": nq_ret}, axis=1).dropna()
    if asof:
        aligned = aligned[aligned.index <= asof]
    if len(aligned) < 2:
        raise ValueError("not enough aligned ES/NQ returns")

    last = aligned.iloc[-1]
    window = aligned.tail(20)
    beta = float(window["nq"].cov(window["es"]) / window["es"].var()) if window["es"].var() > 0 else None
    corr = float(window["nq"].corr(window["es"])) if len(window) >= 5 else None
    ratio = (nq.set_index("date")["close"] / es.set_index("date")["close"]).dropna()
    ratio = ratio[ratio.index <= (asof or ratio.index[-1])].tail(20)
    spread_z = float((ratio.iloc[-1] - ratio.mean()) / ratio.std()) if len(ratio) >= 5 and ratio.std() > 0 else None

    flags: list[str] = []
    vix_level = vix_change = None
    vx_available = False
    proxy = "NONE"
    if vix is not None and not vix.empty:
        series = vix.set_index("date")["close"].astype(float)
        if asof:
            series = series[series.index <= asof]
        if not series.empty:
            vix_level = float(series.iloc[-1])
            vix_change = float(series.iloc[-1] / series.iloc[-6] - 1.0) if len(series) >= 6 else None
            proxy = "VIX_SPOT_PROXY"
            flags.append("VX_FUTURES_UNAVAILABLE")

    def last_return(frame: pd.DataFrame | None) -> float | None:
        if frame is None or frame.empty:
            return None
        series = _returns(frame)
        if asof:
            series = series[series.index <= asof]
        return float(series.iloc[-1]) if not series.empty else None

    zn_ret = last_return(zn)
    zb_ret = last_return(zb)
    if zn is not None or zb is not None:
        flags.append("ZN_ZB_YAHOO_PROXY")

    dxy_level = None
    if dxy is not None and not dxy.empty:
        series = dxy.set_index("date")["close"].astype(float)
        if asof:
            series = series[series.index <= asof]
        dxy_level = float(series.iloc[-1]) if not series.empty else None

    return IntermarketState(
        asof=str(asof or aligned.index[-1]),
        es_return_1d=round(float(last["es"]), 6),
        nq_return_1d=round(float(last["nq"]), 6),
        relative_1d=round(float(last["nq"] - last["es"]), 6),
        beta_20d=round(beta, 4) if beta is not None else None,
        corr_20d=round(corr, 4) if corr is not None else None,
        spread_z_20d=round(spread_z, 4) if spread_z is not None else None,
        vix_level=round(vix_level, 4) if vix_level is not None else None,
        vix_change_5d=round(vix_change, 6) if vix_change is not None else None,
        vx_futures_available=vx_available,
        vix_proxy=proxy,
        zn_return_1d=round(zn_ret, 6) if zn_ret is not None else None,
        zb_return_1d=round(zb_ret, 6) if zb_ret is not None else None,
        dxy_level=round(dxy_level, 4) if dxy_level is not None else None,
        flags=flags,
    )
