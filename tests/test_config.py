import pytest

from fudan_web_tool.config import ConfigError, load_config


def test_load_config_reads_env_values(monkeypatch):
    monkeypatch.setenv("FUDAN_NET_USERNAME", "test-user")
    monkeypatch.setenv("FUDAN_NET_PASSWORD", "secret")
    monkeypatch.setenv("FUDAN_NET_BASE_URL", "http://10.102.250.36/")
    monkeypatch.setenv("FUDAN_NET_CHANNEL_NAME", "\u6821\u56ed\u7f51")
    monkeypatch.setenv("FUDAN_NET_INTERVAL", "15")
    monkeypatch.setenv("FUDAN_NET_CHECK_TIMEOUT", "2.5")
    monkeypatch.setenv(
        "FUDAN_NET_CHECK_URLS",
        "http://connect.rom.miui.com/generate_204, https://www.baidu.com",
    )

    config = load_config(load_dotenv_file=False)

    assert config.username == "test-user"
    assert config.password == "secret"
    assert config.base_url == "http://10.102.250.36"
    assert config.channel_name == "\u6821\u56ed\u7f51"
    assert config.interval == 15
    assert config.check_timeout == 2.5
    assert config.check_urls == (
        "http://connect.rom.miui.com/generate_204",
        "https://www.baidu.com",
    )


def test_load_config_rejects_missing_credentials(monkeypatch):
    monkeypatch.delenv("FUDAN_NET_USERNAME", raising=False)
    monkeypatch.delenv("FUDAN_NET_PASSWORD", raising=False)

    with pytest.raises(ConfigError) as excinfo:
        load_config(load_dotenv_file=False)

    assert "FUDAN_NET_USERNAME" in str(excinfo.value)
    assert "FUDAN_NET_PASSWORD" in str(excinfo.value)


def test_load_config_can_skip_credentials_for_status(monkeypatch):
    monkeypatch.delenv("FUDAN_NET_USERNAME", raising=False)
    monkeypatch.delenv("FUDAN_NET_PASSWORD", raising=False)

    config = load_config(load_dotenv_file=False, require_credentials=False)

    assert config.username == ""
    assert config.password == ""
    assert config.base_url == "http://10.102.250.36"
    assert config.interval == 5
    assert config.check_timeout == 3.0
