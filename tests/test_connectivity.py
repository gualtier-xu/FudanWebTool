import httpx
import logging
import time

from fudan_web_tool.connectivity import ConnectivityChecker


def test_connectivity_checker_uses_trust_env_false():
    checker = ConnectivityChecker(("https://www.baidu.com",))

    assert checker.client.trust_env is False
    assert checker.client.timeout.connect == 3.0
    checker.close()


def test_connectivity_uses_fast_probe_before_http_check():
    http_requests = []

    def handler(request):
        http_requests.append(str(request.url))
        return httpx.Response(204)

    def fast_probe(url, timeout):
        return url == "https://fast.example"

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    checker = ConnectivityChecker(
        ("https://slow.example", "https://fast.example"),
        client=client,
        fast_probe=fast_probe,
    )
    try:
        result = checker.check()
    finally:
        checker.close()

    assert result.is_online is True
    assert result.successful_url == "https://fast.example"
    assert http_requests == ["https://fast.example"]


def test_connectivity_returns_offline_when_fast_probes_fail():
    http_requests = []

    def handler(request):
        http_requests.append(str(request.url))
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    checker = ConnectivityChecker(
        ("https://one.example", "https://two.example"),
        client=client,
        fast_probe=lambda url, timeout: False,
    )
    try:
        result = checker.check()
    finally:
        checker.close()

    assert result.is_online is False
    assert http_requests == []
    assert {attempt.error for attempt in result.attempts} == {"fast connectivity probe failed"}


def test_connectivity_logs_before_each_attempt(caplog):
    def handler(request):
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    checker = ConnectivityChecker(("http://connect.rom.miui.com/generate_204",), client=client)
    try:
        with caplog.at_level(logging.INFO):
            checker.check()
    finally:
        checker.close()

    assert "Checking external connectivity: http://connect.rom.miui.com/generate_204" in caplog.text
    assert "External connectivity succeeded: http://connect.rom.miui.com/generate_204" in caplog.text


def test_connectivity_logs_failed_attempt(caplog):
    def handler(request):
        raise httpx.ConnectError("network unreachable", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    checker = ConnectivityChecker(("https://blocked.example",), client=client)
    try:
        with caplog.at_level(logging.INFO):
            result = checker.check()
    finally:
        checker.close()

    assert result.is_online is False
    assert "External connectivity failed: https://blocked.example" in caplog.text


def test_connectivity_succeeds_when_any_target_is_reachable():
    def handler(request):
        if request.url.host == "blocked.example":
            raise httpx.ConnectError("blocked", request=request)
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    checker = ConnectivityChecker(
        ("https://blocked.example", "http://connect.rom.miui.com/generate_204"),
        client=client,
    )
    try:
        result = checker.check()
    finally:
        checker.close()

    assert result.is_online is True
    assert result.successful_url == "http://connect.rom.miui.com/generate_204"


def test_connectivity_checks_targets_in_parallel():
    def handler(request):
        if request.url.host == "slow.example":
            time.sleep(0.2)
            raise httpx.ConnectError("slow failure", request=request)
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    checker = ConnectivityChecker(
        ("https://slow.example", "http://connect.rom.miui.com/generate_204"),
        client=client,
        timeout=1,
    )
    started = time.perf_counter()
    try:
        result = checker.check()
    finally:
        checker.close()
    elapsed = time.perf_counter() - started

    assert result.is_online is True
    assert result.successful_url == "http://connect.rom.miui.com/generate_204"
    assert elapsed < 0.15


def test_connectivity_returns_offline_when_all_targets_timeout(caplog):
    def handler(request):
        time.sleep(0.2)
        return httpx.Response(204)

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    checker = ConnectivityChecker(
        ("https://slow-one.example", "https://slow-two.example"),
        client=client,
        timeout=0.05,
    )
    started = time.perf_counter()
    try:
        with caplog.at_level(logging.INFO):
            result = checker.check()
    finally:
        checker.close()
    elapsed = time.perf_counter() - started

    assert result.is_online is False
    assert elapsed < 0.15
    assert {attempt.error for attempt in result.attempts} == {"connectivity check timed out"}
    assert "External connectivity timed out: https://slow-one.example" in caplog.text
    assert "External connectivity timed out: https://slow-two.example" in caplog.text


def test_connectivity_rejects_captive_portal_content():
    def handler(request):
        return httpx.Response(200, text="<title>authenticate</title>璁よ瘉鐧诲綍")

    client = httpx.Client(transport=httpx.MockTransport(handler), trust_env=False)
    checker = ConnectivityChecker(("https://example.com",), client=client)
    try:
        result = checker.check()
    finally:
        checker.close()

    assert result.is_online is False
    assert "captive portal" in result.attempts[0].error
