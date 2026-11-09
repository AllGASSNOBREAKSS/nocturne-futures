"""Phase 3U: polite collection, revision ledger and point-in-time guarantees."""
import gzip

import numpy as np
import pandas as pd
import pytest

from nocturne.collector.http import AccessDenied, FetchFailed, PoliteClient
from nocturne.collector.sources import FRED_RULES, _after_bdays, classify_fed, cot_available_at
from nocturne.collector.store import Archive
from nocturne.research import free_data_experiment as fx
from nocturne.research.orchestrator import JOB_TYPES, SHADOW_TYPES, JobStore


class FakeResponse:
    def __init__(self, status, content=b"ok", headers=None, text=""):
        self.status_code, self.content, self.headers, self.text, self.url = status, content, headers or {}, text, "u"


class FakeSession:
    def __init__(self, robots="", responses=()):
        self.robots, self.responses, self.calls = robots, list(responses), []

    def get(self, url, params=None, headers=None, timeout=None):
        if url.endswith("/robots.txt"):
            return FakeResponse(200, text=self.robots) if self.robots is not None else FakeResponse(404)
        self.calls.append(url)
        return self.responses.pop(0)


class Clock:
    def __init__(self):
        self.now, self.slept = 0.0, []

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def client(session, **kw):
    clock = Clock()
    return PoliteClient(session=session, sleep=clock.sleep, clock=clock, **kw), clock


def test_crawl_respects_robots_but_documented_api_records_it():
    session = FakeSession(robots="User-agent: *\nDisallow: /", responses=[FakeResponse(200)])
    c, _ = client(session)
    with pytest.raises(AccessDenied):
        c.get("https://example.org/page", access="crawl")
    assert c.get("https://example.org/api").status == 200
    assert c.log[-1]["robots_allows"] is False and c.log[-1]["access"] == "api"


def test_missing_robots_allows_crawl_per_rfc9309():
    c, _ = client(FakeSession(robots=None, responses=[FakeResponse(200)]))
    assert c.get("https://example.org/feed.xml", access="crawl").status == 200


def test_per_domain_spacing_and_retry_after_backoff():
    session = FakeSession(responses=[FakeResponse(200), FakeResponse(429, headers={"Retry-After": "7"}), FakeResponse(200)])
    c, clock = client(session, intervals={"example.org": 5.0})
    c.get("https://example.org/a")
    clock.now += 1.0
    response = c.get("https://example.org/b")
    assert response.attempts == 2
    assert pytest.approx(clock.slept[0]) == 4.0  # spacing before second request
    assert 7.0 in clock.slept  # honoured Retry-After


def test_forbidden_is_access_denied_and_retries_are_bounded():
    c, _ = client(FakeSession(responses=[FakeResponse(403)]))
    with pytest.raises(AccessDenied):
        c.get("https://example.org/x")
    c, _ = client(FakeSession(responses=[FakeResponse(503)] * 4), retries=3)
    with pytest.raises(FetchFailed):
        c.get("https://example.org/x")
    c, _ = client(FakeSession(responses=[FakeResponse(200, content=b"x" * 11)]), max_bytes=10)
    with pytest.raises(FetchFailed, match="budget"):
        c.get("https://example.org/x")


def test_archive_detects_unchanged_appended_and_revised_rows(tmp_path):
    archive = Archive(tmp_path)
    first = pd.DataFrame({"date": ["2026-01-01", "2026-01-02"], "value": [1.0, 2.0]})
    assert archive.record("s", "d", b"raw1", first, ["date"], {})["status"] == "NEW"
    assert archive.record("s", "d", b"raw1", first, ["date"], {})["status"] == "UNCHANGED"
    revised = pd.DataFrame({"date": ["2026-01-01", "2026-01-02", "2026-01-03"], "value": [1.0, 2.5, 3.0]})
    entry = archive.record("s", "d", b"raw2", revised, ["date"], {})
    assert (entry["status"], entry["appended_rows"], entry["revised_rows"]) == ("UPDATED", 1, 1)
    assert entry["revised_examples"] == [{"date": "2026-01-02"}]
    assert len(list((tmp_path / "s/d/raw").glob("*.gz"))) == 2
    assert gzip.decompress((tmp_path / f"s/d/raw/{entry['raw_sha256']}.gz").read_bytes()) == b"raw2"
    assert len(archive.manifest("s", "d")) == 3


def test_archive_rejects_duplicates_and_tampering(tmp_path):
    archive = Archive(tmp_path)
    with pytest.raises(ValueError, match="duplicate"):
        archive.record("s", "d", b"r", pd.DataFrame({"k": [1, 1], "v": [1, 2]}), ["k"], {})
    entry = archive.record("s", "d", b"r", pd.DataFrame({"k": [1], "v": [1]}), ["k"], {})
    (tmp_path / f"s/d/normalized/{entry['normalized_sha256']}.csv").write_text("k,v\n1,9\n")
    with pytest.raises(ValueError, match="checksum"):
        archive.load("s", "d")
    with pytest.raises(ValueError):
        archive.record("../escape", "d", b"r", pd.DataFrame({"k": [2]}), ["k"], {})


def test_fred_availability_lags_skip_weekends():
    friday = pd.Series(["2026-11-06"])
    assert str(_after_bdays(friday, FRED_RULES["VIXCLS"][0])[0]) == "2026-11-06 22:00:00+00:00"
    assert str(_after_bdays(friday, FRED_RULES["DGS10"][0])[0]) == "2026-11-09 22:00:00+00:00"
    assert not FRED_RULES["USREC"][1] and not FRED_RULES["CPIAUCSL"][1]


def test_cot_availability_is_conservative_including_shutdowns():
    out = cot_available_at(pd.Series(["2026-11-03", "2018-12-25", "2013-10-08"]))
    assert str(out[0]) == "2026-11-09 21:00:00+00:00"  # Tuesday -> following Monday
    assert str(out[1]) == "2019-03-09 21:00:00+00:00"
    assert str(out[2]) == "2013-11-30 21:00:00+00:00"


def test_asof_join_never_uses_values_published_after_cutoff():
    source = pd.DataFrame({"available_at": pd.to_datetime(["2026-01-01 22:00", "2026-01-02 22:00", "2026-01-30 22:00"], utc=True),
                           "x": [1.0, 2.0, 3.0]})
    cutoffs = pd.Series(pd.to_datetime(["2026-01-02 21:59", "2026-01-03 00:00", "2026-01-29 00:00"], utc=True))
    merged = fx._asof(cutoffs, source, ["x"], tolerance_days=10)
    assert merged.x.iloc[0] == 1.0 and merged.x.iloc[1] == 2.0
    assert np.isnan(merged.x.iloc[2])  # stale beyond tolerance -> missing, never forward-filled
    assert (merged.available_at.dropna() <= merged.cutoff[merged.available_at.notna()]).all()


def test_fed_title_classification_is_rule_based():
    assert classify_fed("Federal Reserve issues FOMC statement") == "FOMC_STATEMENT"
    assert classify_fed("Minutes of the Federal Open Market Committee, October 27-28") == "FOMC_MINUTES"
    assert classify_fed("Agencies announce new board member") == "OTHER_PRESS_RELEASE"


def comparison(dev_a, dev_b, exp_a, exp_b):
    def c(ci, mean):
        return {"mean": mean, "ci95": ci}
    return {"development": {"a": c(dev_a, sum(dev_a) / 2), "b": c(dev_b, sum(dev_b) / 2)},
            "exposed": {"a": c([exp_a] * 2, exp_a), "b": c([exp_b] * 2, exp_b)}}


def test_preregistered_verdict_rule():
    decide = lambda comp: fx.verdicts({era: {"brier_free_minus_frequency": v["a"], "brier_free_minus_base": v["b"],
                                             "pinball_free_minus_trailing": v["a"], "pinball_free_minus_base": v["b"]}
                                       for era, v in comp.items()})["direction_free_features"]
    assert decide(comparison([-.02, -.01], [-.02, -.01], -.01, -.01)) == "PASS"
    assert decide(comparison([-.02, -.01], [-.02, -.01], -.01, .01)) == "INCONCLUSIVE"  # exposed sign flips
    assert decide(comparison([-.02, .01], [-.02, .01], -.01, -.01)) == "INCONCLUSIVE"
    assert decide(comparison([-.02, -.01], [.001, .01], -.01, -.01)) == "FAIL"


def test_hypothetical_strategy_costs_reduce_expectancy_and_dead_zone_is_flat():
    frame = pd.DataFrame({"p": [.6, .4, .51, .7], "next_return": [.01, -.01, .05, -.002]})
    out = fx.strategy(frame, "p")
    assert out["0bps"]["trades"] == 3  # 0.51 is inside the dead zone
    assert out["5bps"]["net_expectancy_fraction"] < out["0bps"]["net_expectancy_fraction"]


def test_free_data_jobs_are_research_lane_only(tmp_path):
    store = JobStore(tmp_path)
    for kind in ("FREE_DATA_COLLECTION", "FREE_DATA_EXPERIMENT"):
        assert kind in JOB_TYPES and kind not in SHADOW_TYPES
        store.submit(kind, "research", "k")
        with pytest.raises(ValueError):
            store.submit(kind, "shadow", "k")
