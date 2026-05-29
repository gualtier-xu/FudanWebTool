import logging

from fudan_web_tool.config import AppConfig
from fudan_web_tool.recovery import RecoveryManager


class FakeConnectivity:
    def __init__(self, results):
        self.results = list(results)

    def check(self):
        return self.results.pop(0)


class FakePortal:
    def __init__(self, online):
        self.online = online
        self.calls = []

    def get_ip(self):
        self.calls.append(("get_ip",))
        return "10.102.122.161"

    def get_auth_status(self, ip_address):
        self.calls.append(("get_auth_status", ip_address))
        return type("AuthStatus", (), {"is_online": self.online, "raw": {}})()

    def logout(self, username, ip_address):
        self.calls.append(("logout", username, ip_address))
        return type("LoginResult", (), {"success": True, "message": "ok", "data": {}})()

    def login(self, username, password, ip_address, channel_name):
        self.calls.append(("login", username, password, ip_address, channel_name))
        return type("LoginResult", (), {"success": True, "message": "ok", "data": {}})()


def config():
    return AppConfig(
        username="test-user",
        password="secret",
        base_url="http://10.102.250.36",
        channel_name="\u6821\u56ed\u7f51",
        interval=30,
        check_timeout=1.0,
        check_urls=("https://www.baidu.com",),
    )


def offline_result():
    return type("ConnectivityResult", (), {"is_online": False, "successful_url": None})()


def online_result():
    return type(
        "ConnectivityResult",
        (),
        {"is_online": True, "successful_url": "https://www.baidu.com"},
    )()


def test_recovery_does_nothing_when_external_network_is_online():
    portal = FakePortal(online=True)
    manager = RecoveryManager(config(), portal, FakeConnectivity([online_result()]))

    result = manager.run_once()

    assert result.action == "already_online"
    assert portal.calls == []


def test_recovery_logs_out_before_login_when_portal_is_falsely_online():
    portal = FakePortal(online=True)
    manager = RecoveryManager(config(), portal, FakeConnectivity([offline_result()]))

    result = manager.run_once()

    assert result.action == "relogin"
    assert portal.calls == [
        ("get_ip",),
        ("get_auth_status", "10.102.122.161"),
        ("logout", "test-user", "10.102.122.161"),
        ("login", "test-user", "secret", "10.102.122.161", "\u6821\u56ed\u7f51"),
    ]


def test_recovery_logs_do_not_include_password(caplog):
    portal = FakePortal(online=True)
    manager = RecoveryManager(config(), portal, FakeConnectivity([offline_result()]))

    manager.run_once()

    assert "secret" not in caplog.text


def test_recovery_logs_detailed_reconnect_steps(caplog):
    portal = FakePortal(online=True)
    manager = RecoveryManager(config(), portal, FakeConnectivity([offline_result()]))

    with caplog.at_level(logging.INFO):
        manager.run_once()

    assert "Starting one recovery cycle" in caplog.text
    assert "External network is offline" in caplog.text
    assert "Fetching portal IP address" in caplog.text
    assert "Portal IP address: 10.102.122.161" in caplog.text
    assert "Portal auth state: online" in caplog.text
    assert "False-online state detected" in caplog.text
    assert "Logout request completed" in caplog.text
    assert "Login request completed for channel" in caplog.text
    assert "secret" not in caplog.text


def test_recovery_logs_in_directly_when_portal_is_offline():
    portal = FakePortal(online=False)
    manager = RecoveryManager(config(), portal, FakeConnectivity([offline_result()]))

    result = manager.run_once()

    assert result.action == "login"
    assert ("logout", "test-user", "10.102.122.161") not in portal.calls
    assert portal.calls[-1] == (
        "login",
        "test-user",
        "secret",
        "10.102.122.161",
        "\u6821\u56ed\u7f51",
    )
