"""Nocturne desktop backend: loopback-only FastAPI for the Electron terminal.

Started by the desktop app with a random per-launch admin token in
NOCTURNE_DESKTOP_TOKEN. The token never reaches the renderer: the Electron
main process attaches it. Mutations are an explicit admin allow-list (start or
cancel research jobs, issue baseline forecasts, save configs, refresh free
data). There are no order, broker or live-data routes. NO_TRADE everywhere.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import re
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import Response

from .api.security import SecurityMiddleware, SecurityPolicy, TOKEN
from .shadow.locking import FileLock
from .studio import (ROOT, STATE, backtest, dataset, forecasts, indicators, insights, jobs, live, market, modelsignals, news, predictor,
                     rules, sweep, training)

VERSION = "4.0.0"
ID = r"[a-f0-9]{24}"
ROOT_RE = r"(NQ|ES)"
MUTATIONS = (("POST", r"/v1/backtests"), ("POST", r"/v1/sweeps"), ("POST", r"/v1/training-jobs"), ("POST", rf"/v1/jobs/{ID}/cancel"),
             ("POST", rf"/v1/forecasts/sessions/{ROOT_RE}/issue"), ("POST", r"/v1/configs/(strategy|model)"),
             ("POST", r"/v1/data/refresh"), ("POST", rf"/v1/predict/{ROOT_RE}"))
ROUTES = ((rf"/v1/markets/{ROOT_RE}/[a-z]+", "/v1/markets/{root}/{view}"), (rf"/v1/levels/{ROOT_RE}", "/v1/levels/{root}"),
          (rf"/v1/(backtests|training-jobs|sweeps|jobs)/{ID}(/[a-z.]+)?", "/v1/{jobs}/{id}"),
          (rf"/v1/(live|news)/{ROOT_RE}(/quote)?", "/v1/{view}/{root}"),
          (rf"/v1/forecasts/sessions/{ROOT_RE}/issue", "/v1/forecasts/sessions/{root}/issue"),
          (r"/v1/[a-z/-]+", "/v1/{resource}"))


class RotatingAudit:
    """Secret-free audit records with bounded rotation (desktop polling is frequent)."""

    def __init__(self, path, max_bytes=4 * 1024**2):
        self.path, self.max_bytes = Path(path), max_bytes

    def __call__(self, record):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(self.path.with_suffix(".lock")):
            if self.path.exists() and self.path.stat().st_size > self.max_bytes:
                self.path.replace(self.path.with_suffix(".1.jsonl"))
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")


_refresh = {"state": "IDLE"}
_warm = {}


def _warm_predictor():
    """Train/load the prediction models in the background so the first click is instant."""
    for root in market.ROOTS:
        _warm[root] = "TRAINING"
        try:
            if market.databento_available(root):
                predictor.load_or_train(root)
                predictor.track_record(root)
                _warm[root] = "READY"
            else:
                _warm[root] = "NO_DATABENTO_DATA"
        except Exception as exc:  # report, never crash the server
            _warm[root] = f"FAILED: {type(exc).__name__}"


def _refresh_data():
    _refresh.update(state="RUNNING", started_at=datetime.now(timezone.utc).isoformat())
    report = STATE / "refresh.json"
    try:
        code = subprocess.run([sys.executable, "scripts/phase3u_collect.py", "--sources", "yahoo_futures,fred,cftc,sec,fed",
                               "--root", str(ROOT / "data/research/free"), "--report", str(report)],
                              cwd=ROOT, capture_output=True, timeout=900).returncode
        detail = json.loads(report.read_text()) if report.exists() else {}
        _refresh.update(state="COMPLETED" if code == 0 else "PARTIAL", exit_code=code,
                        sources={k: v["status"] for k, v in detail.get("sources", {}).items()})
    except (OSError, subprocess.TimeoutExpired) as exc:
        _refresh.update(state="FAILED", reason=type(exc).__name__)
    _refresh["finished_at"] = datetime.now(timezone.utc).isoformat()
    market._load.cache_clear()


def create_app(token: str, worker: jobs.Worker | None = None) -> FastAPI:
    if not TOKEN.fullmatch(token or ""):
        raise ValueError("desktop token must be 32-128 URL-safe characters")
    policy = SecurityPolicy(admin_digest=hashlib.sha256(token.encode()).digest(), peer_per_minute=1000,
                            principal_per_minute=1000, max_body=262144)
    app = FastAPI(title="Nocturne Desktop API", version=VERSION, docs_url=None, redoc_url=None, openapi_url=None)
    app.add_middleware(SecurityMiddleware, policy=policy, audit=RotatingAudit(STATE / "audit/desktop-api.jsonl"),
                       mutations=MUTATIONS, routes=ROUTES)

    def guard(fn, *args, **kwargs):
        try:
            return market.json_safe(fn(*args, **kwargs))
        except ValueError as exc:
            raise HTTPException(422, str(exc)[:300]) from None
        except FileNotFoundError:
            raise HTTPException(404, "artifact not found") from None

    @app.get("/health")
    def health():
        return {"status": "alive"}

    @app.get("/v1/system/health")
    def system_health():
        return {"status": "OK", "version": VERSION, "time": datetime.now(timezone.utc).isoformat(),
                "worker": {"alive": bool(worker and worker.is_alive()), "last_tick": worker.last if worker else None},
                "refresh": _refresh, "mode": "LOCAL_DESKTOP_LOOPBACK", "live_data": False, "broker_execution": False,
                "trading_decision": "NO_TRADE"}

    @app.get("/v1/data/datasets")
    def datasets():
        return guard(market.datasets)

    @app.post("/v1/data/refresh")
    def refresh():
        if _refresh.get("state") == "RUNNING":
            return {"status": "ALREADY_RUNNING", **_refresh}
        threading.Thread(target=_refresh_data, daemon=True).start()
        return {"status": "STARTED", "note": "free Yahoo/FRED/CFTC/SEC/Fed refresh into the ignored operational archive"}

    @app.get("/v1/markets/{root}/bars")
    def bars(root: str, interval: str = Query("5m", pattern=r"^(1m|5m|15m|1h|4h|1d|1w)$"),
             start: str | None = Query(None, max_length=32), end: str | None = Query(None, max_length=32),
             limit: int = Query(3000, ge=10, le=50000), source: str | None = Query(None, pattern=r"^(databento|yahoo)$")):
        def build():
            frame, meta = market.bars(root, interval, start, end, limit, source=source)
            return {"meta": meta, "bars": [{"t": int(r.timestamp.timestamp()), "o": r.open, "h": r.high, "l": r.low, "c": r.close, "v": r.volume}
                                           for r in frame.itertuples()]}
        return guard(build)

    @app.get("/v1/markets/{root}/indicators")
    def indicator_series(root: str, interval: str = Query("5m", pattern=r"^(1m|5m|15m|1h|4h|1d|1w)$"),
                         names: str = Query("vwap", max_length=400), limit: int = Query(3000, ge=10, le=50000),
                         source: str | None = Query(None, pattern=r"^(databento|yahoo)$")):
        def build():
            frame, meta = market.bars(root, interval, limit=limit + 400, source=source)
            out = {}
            for item in names.split(","):
                if not re.fullmatch(r"[a-z_]+(:[0-9.]+)*", item):
                    raise ValueError(f"bad indicator spec {item}")
                name, *values = item.split(":")
                keys = list(indicators.CATALOG.get(name, {}).get("params", {}))
                series = indicators.compute(frame, name, {k: float(v) for k, v in zip(keys, values)})
                tail = series.tail(limit)
                out[item] = [{"t": int(t.timestamp()), "v": round(float(v), 4)} for t, v in zip(frame.timestamp.tail(limit), tail) if v == v]
            return {"meta": meta, "series": out}
        return guard(build)

    @app.get("/v1/markets/{root}/regime")
    def regime(root: str):
        return guard(market.regime, root)

    @app.get("/v1/markets/{root}/sessions")
    def sessions(root: str):
        def build():
            frame, meta = market.session_ranges(root)
            frame = frame.sort_values("session_date").groupby("session").tail(60)
            return {"meta": meta, "sessions": frame.assign(session_date=frame.session_date.astype(str))[["session_date", "session", "high", "low", "range"]].to_dict("records")}
        return guard(build)

    @app.get("/v1/levels/{root}")
    def levels(root: str):
        if root not in market.ROOTS:
            raise HTTPException(422, "unsupported instrument")
        return guard(market.levels, root)

    @app.get("/v1/indicators/catalog")
    def catalog():
        return {"indicators": indicators.CATALOG, "unavailable": indicators.UNAVAILABLE, "operators": rules.OPS,
                "sessions": rules.SESSIONS, "strategies": backtest.BUILTIN_PARAMS, "intervals": backtest.INTERVALS,
                "models": training.MODELS, "objectives": training.OBJECTIVES,
                "feature_families": {k: v for k, v in training.FAMILIES.items()},
                "databento": {"objectives": training.DB_OBJECTIVES, "descriptions": dataset.OBJECTIVES,
                              "point_thresholds": dataset.POINT_THRESHOLDS, "atr_thresholds": dataset.ATR_THRESHOLDS,
                              "tbs_geometries": list(dataset.TBS_GEOMETRIES),
                              "feature_families": {"price": dataset.PRICE, "intraday": dataset.INTRADAY,
                                                   **{k: v for k, v in training.FAMILIES.items() if k != "price"}},
                              "available": market.databento_available("NQ")},
                "model_strategies": modelsignals.KINDS, "max_contracts": backtest.MAX_CONTRACTS,
                "sweep": {"catalog": [{"label": c["label"], "family": c["family"], "strategy": c["strategy"]} for c in sweep.CATALOG],
                          "rr_default": sweep.RR_DEFAULT}}

    @app.get("/v1/forecasts/sessions")
    def session_forecasts(root: str = Query("NQ", pattern=r"^(NQ|ES)$")):
        return guard(lambda: {**forecasts.history(root), "retrospective": forecasts.retrospective_calibration(root)})

    @app.post("/v1/forecasts/sessions/{root}/issue")
    def issue(root: str):
        def run():
            record = forecasts.issue(root)
            return {"forecast": record, "outcomes_written": forecasts.evaluate()}
        return guard(run)

    @app.get("/v1/forecasts/ndx-shadow")
    def ndx_shadow():
        def build():
            journal = ROOT / "data/shadow/ndx_range"
            lines = lambda p: [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []
            status_path = ROOT / "reports/phase3h_shadow_status.json"
            status = json.loads(status_path.read_text(encoding="utf-8-sig")) if status_path.exists() else {}
            # Verbatim immutable journal rows; never edited by the desktop app.
            return {"forecasts": lines(journal / "forecasts.jsonl"), "outcomes": lines(journal / "outcomes.jsonl"),
                    "quarantined": status.get("quarantined_forecast_ids"), "operational_status": status.get("operational_status"),
                    "status_at": status.get("generated_at"), "report": insights._report("phase3u_forward.json")}
        return guard(build)

    @app.post("/v1/predict/{root}")
    def predict(root: str):
        """Run every validated model for the next session and journal the result once."""
        if root not in market.ROOTS:
            raise HTTPException(422, "unsupported instrument")
        return guard(predictor.predict, root)

    @app.get("/v1/predict/{root}/status")
    def predict_status(root: str):
        return {"ready": _warm.get(root) == "READY", "state": _warm.get(root, "PENDING")}

    @app.get("/v1/configs/{kind}")
    def configs(kind: str):
        return guard(insights.list_configs, kind)

    @app.post("/v1/configs/{kind}")
    def save(kind: str, body: dict = Body(...)):
        def run():
            config = body.get("config") or {}
            errors = (rules.validate(config) if kind == "strategy" and config.get("side") else [])
            if errors:
                raise ValueError("; ".join(errors))
            return insights.save_config(kind, body.get("name"), config)
        return guard(run)

    @app.post("/v1/backtests")
    def start_backtest(body: dict = Body(...)):
        return guard(jobs.submit, "backtest", body)

    @app.get("/v1/backtests")
    def list_backtests():
        return guard(jobs.list_jobs, "backtest")

    @app.post("/v1/training-jobs")
    def start_training(body: dict = Body(...)):
        return guard(jobs.submit, "training", body)

    @app.post("/v1/sweeps")
    def start_sweep(body: dict = Body(...)):
        return guard(jobs.submit, "sweep", body)

    @app.get("/v1/sweeps")
    def list_sweeps():
        return guard(jobs.list_jobs, "sweep")

    @app.get("/v1/live/{root}")
    def live_view(root: str):
        if root not in market.ROOTS:
            raise HTTPException(422, "unsupported instrument")
        try:
            return live.snapshot(root)
        except RuntimeError as exc:  # upstream fetch failure: tell the UI plainly
            raise HTTPException(503, f"Free intraday feed unavailable right now ({str(exc)[:120]})")

    @app.get("/v1/live/{root}/quote")
    def live_quote(root: str):
        if root not in market.ROOTS:
            raise HTTPException(422, "unsupported instrument")
        try:
            return live.quote(root)
        except RuntimeError as exc:
            raise HTTPException(503, f"Free intraday feed unavailable right now ({str(exc)[:120]})")

    @app.get("/v1/news/{root}")
    def news_view(root: str):
        if root not in market.ROOTS:
            raise HTTPException(422, "unsupported instrument")
        def build():
            try:
                one = live.fetch(root)["one"]
            except Exception:  # noqa: BLE001 - headlines still useful without price reaction
                one = None
            return news.brief(root, one)
        return guard(build)

    @app.get("/v1/training-jobs")
    def list_training():
        return guard(jobs.list_jobs, "training")

    def job_detail(identifier: str):
        result = guard(jobs.get, identifier)
        if result is None:
            raise HTTPException(404, "job not found")
        return result

    app.get("/v1/backtests/{identifier}")(job_detail)
    app.get("/v1/training-jobs/{identifier}")(job_detail)
    app.get("/v1/jobs/{identifier}")(job_detail)

    @app.get("/v1/backtests/{identifier}/trades.csv")
    def trades_csv(identifier: str):
        job = jobs.get(identifier, detail=False)
        if job is None or not job.get("attempts"):
            raise HTTPException(404, "job not found")
        path = jobs.STORE_ROOT / "attempts" / identifier / str(job["attempts"]) / "trades.csv"
        if not path.exists():
            raise HTTPException(404, "no trade ledger")
        return Response(path.read_bytes(), media_type="text/csv")

    @app.post("/v1/jobs/{identifier}/cancel")
    def cancel(identifier: str):
        return jobs.cancel(identifier)

    @app.get("/v1/models")
    def models():
        def build():
            frozen = []
            for path in sorted((ROOT / "models").rglob("*.json"))[:50]:
                try:
                    meta = json.loads(path.read_text(encoding="utf-8-sig"))
                except ValueError:
                    continue
                if isinstance(meta, dict) and (meta.get("model_id") or meta.get("validation_status")):
                    frozen.append({"path": str(path.relative_to(ROOT)), **{k: meta.get(k) for k in ("model_id", "model_version", "validation_status", "trained_at", "objective")}})
            experiments = [j for j in jobs.list_jobs("training") if j["state"] == "SUCCEEDED"]
            return {"frozen": frozen, "experiments": experiments,
                    "governance": "All models research-only; promotion requires independent validation and separate authorization."}
        return guard(build)

    @app.get("/v1/research")
    def research():
        return guard(insights.research)

    @app.get("/v1/signals")
    def signals():
        def build():
            ranking = insights._report("phase3v_signal_ranking.json") or {}
            studio = [{"job_id": j["job_id"], "name": j.get("name"), "verdict": (j.get("result") or {}).get("verdict"),
                       "summary": (j.get("result") or {}).get("summary"), "config": j["config"]}
                      for j in jobs.list_jobs("backtest") if j["state"] == "SUCCEEDED"]
            return {"ranking": ranking, "studio_backtests": studio}
        return guard(build)

    @app.get("/v1/intel")
    def intel():
        return guard(insights.intelligence)

    @app.get("/v1/operations")
    def operations():
        return guard(insights.operations)

    return app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    token = os.environ.pop("NOCTURNE_DESKTOP_TOKEN", "")
    worker = jobs.Worker()
    app = create_app(token, worker)
    worker.start()
    threading.Thread(target=_warm_predictor, daemon=True).start()
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning", access_log=False)


if __name__ == "__main__":
    main()
