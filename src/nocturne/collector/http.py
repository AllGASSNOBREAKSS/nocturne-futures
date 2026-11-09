"""Polite HTTP client: declared user agent, per-domain spacing, retry/backoff.

Documented public APIs are governed by their published API terms (rate limits,
declared user agent); robots.txt is recorded for them but cannot be used to
justify bypassing an API's own rules. Crawl-type access (HTML pages, feeds
without an API contract) must pass robots.txt. RFC 9309: a 4xx robots response
allows access; an unreachable/5xx robots file disallows it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

import requests

USER_AGENT = "NocturneFutures-research/3U (contact: huzaifahmed9890@gmail.com)"
RETRY_STATUS = {429, 500, 502, 503, 504}


class AccessDenied(RuntimeError):
    """The source's rules do not permit this request."""


class FetchFailed(RuntimeError):
    """Retries were exhausted or the response violated a bound."""


@dataclass
class Response:
    url: str
    status: int
    content: bytes
    content_type: str
    attempts: int


@dataclass
class PoliteClient:
    intervals: dict = field(default_factory=dict)  # domain -> minimum seconds between requests
    default_interval: float = 1.0
    retries: int = 3
    backoff: float = 2.0
    max_backoff: float = 60.0
    max_bytes: int = 64 * 1024 * 1024
    timeout: tuple = (10, 90)
    session: object = None
    sleep: object = time.sleep
    clock: object = time.monotonic

    def __post_init__(self):
        self.session = self.session or requests.Session()
        self._last = {}
        self._robots = {}
        self.log = []

    def _domain(self, url):
        return urlsplit(url).netloc.lower()

    def robots(self, url):
        domain = self._domain(url)
        if domain not in self._robots:
            parser = RobotFileParser()
            try:
                response = self.session.get(f"https://{domain}/robots.txt",
                                            headers={"User-Agent": USER_AGENT}, timeout=self.timeout)
                status = response.status_code
                if 400 <= status < 500:
                    parser.allow_all, state = True, f"ABSENT_{status}_ALLOW"
                elif status >= 500:
                    parser.disallow_all, state = True, f"UNREACHABLE_{status}_DISALLOW"
                else:
                    parser.parse(response.text.splitlines())
                    state = "PARSED"
            except requests.RequestException:
                parser.disallow_all, state = True, "UNREACHABLE_DISALLOW"
            self._robots[domain] = (parser, state)
        parser, state = self._robots[domain]
        return {"domain": domain, "state": state, "allowed": parser.can_fetch(USER_AGENT, url)}

    def _wait(self, domain):
        interval = self.intervals.get(domain, self.default_interval)
        last = self._last.get(domain)
        if last is not None:
            remaining = interval - (self.clock() - last)
            if remaining > 0:
                self.sleep(remaining)
        self._last[domain] = self.clock()

    def get(self, url, params=None, access="api", headers=None):
        if access not in ("api", "crawl"):
            raise ValueError("access must be api or crawl")
        robots = self.robots(url)
        if access == "crawl" and not robots["allowed"]:
            raise AccessDenied(f"robots.txt disallows {url}")
        domain = self._domain(url)
        merged = {"User-Agent": USER_AGENT, "Accept-Encoding": "gzip, deflate", **(headers or {})}
        error = None
        for attempt in range(1, self.retries + 2):
            self._wait(domain)
            try:
                response = self.session.get(url, params=params, headers=merged, timeout=self.timeout)
            except requests.RequestException as exc:
                error = f"{type(exc).__name__}"
                delay = None
            else:
                if response.status_code in (401, 403):
                    raise AccessDenied(f"HTTP {response.status_code} from {domain}")
                if response.status_code not in RETRY_STATUS:
                    if response.status_code != 200:
                        raise FetchFailed(f"HTTP {response.status_code} from {domain}")
                    if len(response.content) > self.max_bytes:
                        raise FetchFailed("response exceeded byte budget")
                    self.log.append({"domain": domain, "attempts": attempt, "status": 200, "robots": robots["state"],
                                     "robots_allows": robots["allowed"], "access": access})
                    return Response(response.url, 200, response.content,
                                    response.headers.get("content-type", ""), attempt)
                error = f"HTTP {response.status_code}"
                retry_after = response.headers.get("Retry-After", "")
                delay = float(retry_after) if retry_after.isdigit() else None
            if attempt <= self.retries:
                self.sleep(min(self.max_backoff, delay if delay is not None else self.backoff * 2 ** (attempt - 1)))
        self.log.append({"domain": domain, "attempts": self.retries + 1, "status": error, "robots": robots["state"],
                         "robots_allows": robots["allowed"], "access": access})
        raise FetchFailed(f"{domain}: {error} after {self.retries + 1} attempts")
