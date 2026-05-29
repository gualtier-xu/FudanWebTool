"""External connectivity checks that deliberately bypass system proxies."""

from __future__ import annotations

from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from dataclasses import dataclass
import logging
import socket
import threading
from typing import Callable
from urllib.parse import urlparse

import httpx


LOGGER = logging.getLogger(__name__)
logging.getLogger("httpx").setLevel(logging.WARNING)

CAPTIVE_PORTAL_MARKERS = (
    "authenticate",
    "认证登录",
    "复旦大学",
    "/api/v1/login",
    "useronlinestate",
)


@dataclass(frozen=True)
class CheckAttempt:
    url: str
    ok: bool
    status_code: int | None = None
    error: str = ""


@dataclass(frozen=True)
class ConnectivityResult:
    is_online: bool
    successful_url: str | None
    attempts: tuple[CheckAttempt, ...]


class ConnectivityChecker:
    def __init__(
        self,
        urls: tuple[str, ...],
        *,
        client: httpx.Client | None = None,
        timeout: float = 3.0,
        fast_probe: Callable[[str, float], bool] | None = None,
        fast_timeout: float = 0.75,
    ):
        self.urls = urls
        self.timeout = timeout
        self.fast_timeout = min(fast_timeout, timeout)
        self.fast_probe = fast_probe or (self._always_reachable if client is not None else self._tcp_probe)
        self.client = client or httpx.Client(
            timeout=httpx.Timeout(timeout, connect=timeout, read=timeout, write=timeout, pool=timeout),
            follow_redirects=True,
            trust_env=False,
        )

    def close(self) -> None:
        self.client.close()

    def check(self) -> ConnectivityResult:
        attempts: list[CheckAttempt] = []
        fast_attempts = self._check_fast_connectivity()
        attempts.extend(attempt for attempt in fast_attempts if not attempt.ok)
        reachable_urls = tuple(attempt.url for attempt in fast_attempts if attempt.ok)
        if not reachable_urls:
            return ConnectivityResult(False, None, tuple(attempts))

        finished = threading.Event()
        executor = ThreadPoolExecutor(max_workers=max(1, len(reachable_urls)))
        futures = {executor.submit(self._check_url, url, finished): url for url in reachable_urls}
        pending = set(futures)
        try:
            while pending:
                done, pending = wait(pending, timeout=self.timeout, return_when=FIRST_COMPLETED)
                if not done:
                    for future in pending:
                        LOGGER.warning("External connectivity timed out: %s", futures[future])
                    finished.set()
                    attempts.extend(
                        CheckAttempt(url=futures[future], ok=False, error="connectivity check timed out")
                        for future in pending
                    )
                    return ConnectivityResult(False, None, tuple(attempts))

                for future in done:
                    attempt = future.result()
                    attempts.append(attempt)
                    if attempt.ok:
                        finished.set()
                        for pending_future in pending:
                            pending_future.cancel()
                        return ConnectivityResult(True, attempt.url, tuple(attempts))

            return ConnectivityResult(False, None, tuple(attempts))
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _check_fast_connectivity(self) -> tuple[CheckAttempt, ...]:
        LOGGER.info("Running fast connectivity probes")
        executor = ThreadPoolExecutor(max_workers=max(1, len(self.urls)))
        futures = {
            executor.submit(self._check_fast_url, url): url
            for url in self.urls
        }
        pending = set(futures)
        attempts: list[CheckAttempt] = []
        try:
            while pending:
                done, pending = wait(pending, timeout=self.fast_timeout, return_when=FIRST_COMPLETED)
                if not done:
                    for future in pending:
                        url = futures[future]
                        LOGGER.warning("Fast connectivity probe timed out: %s", url)
                        attempts.append(CheckAttempt(url=url, ok=False, error="fast connectivity probe timed out"))
                    return tuple(attempts)
                for future in done:
                    attempts.append(future.result())
            return tuple(attempts)
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _check_fast_url(self, url: str) -> CheckAttempt:
        LOGGER.info("Fast connectivity probe: %s", url)
        try:
            if self.fast_probe(url, self.fast_timeout):
                LOGGER.info("Fast connectivity probe succeeded: %s", url)
                return CheckAttempt(url=url, ok=True)
        except OSError as exc:
            LOGGER.warning("Fast connectivity probe failed: %s (%s)", url, exc)
            return CheckAttempt(url=url, ok=False, error=str(exc))
        except ValueError as exc:
            LOGGER.warning("Fast connectivity probe failed: %s (%s)", url, exc)
            return CheckAttempt(url=url, ok=False, error=str(exc))

        LOGGER.warning("Fast connectivity probe failed: %s", url)
        return CheckAttempt(url=url, ok=False, error="fast connectivity probe failed")

    def _check_url(self, url: str, finished: threading.Event) -> CheckAttempt:
        LOGGER.info("Checking external connectivity: %s", url)
        try:
            response = self.client.get(url)
        except httpx.HTTPError as exc:
            if not finished.is_set():
                LOGGER.warning("External connectivity failed: %s (%s)", url, exc)
            return CheckAttempt(url=url, ok=False, error=str(exc))

        if self._looks_like_captive_portal(response):
            if not finished.is_set():
                LOGGER.warning(
                    "External connectivity failed: %s (captive portal content detected)",
                    url,
                )
            return CheckAttempt(
                url=url,
                ok=False,
                status_code=response.status_code,
                error="captive portal content detected",
            )

        if 200 <= response.status_code < 400:
            if not finished.is_set():
                LOGGER.info("External connectivity succeeded: %s (HTTP %s)", url, response.status_code)
            return CheckAttempt(url=url, ok=True, status_code=response.status_code)

        if not finished.is_set():
            LOGGER.warning("External connectivity failed: %s (HTTP %s)", url, response.status_code)
        return CheckAttempt(
            url=url,
            ok=False,
            status_code=response.status_code,
            error=f"HTTP {response.status_code}",
        )

    @staticmethod
    def _looks_like_captive_portal(response: httpx.Response) -> bool:
        content_type = response.headers.get("content-type", "")
        if response.status_code == 204:
            return False
        if "text" not in content_type and "html" not in content_type and response.text == "":
            return False
        text = response.text[:5000].lower()
        return any(marker.lower() in text for marker in CAPTIVE_PORTAL_MARKERS)

    @staticmethod
    def _always_reachable(url: str, timeout: float) -> bool:
        return True

    @staticmethod
    def _tcp_probe(url: str, timeout: float) -> bool:
        parsed = urlparse(url)
        if not parsed.hostname:
            raise ValueError("URL must include a host")
        if parsed.port is not None:
            port = parsed.port
        elif parsed.scheme == "https":
            port = 443
        else:
            port = 80

        with socket.create_connection((parsed.hostname, port), timeout=timeout):
            return True
