from pathlib import Path

import pytest

from fudan_web_tool.config import ConfigError, load_config
from fudan_web_tool.settings import JsonSettingsStore, UserSettings


class MemoryCredentials:
    def __init__(self, password=""):
        self.password = password
        self.saved = []

    def get_password(self, username):
        self.saved.append(("get", username))
        return self.password

    def set_password(self, username, password):
        self.saved.append(("set", username, password))
        self.password = password


def test_user_settings_override_env_values_and_password_comes_from_credentials(monkeypatch):
    monkeypatch.setenv("FUDAN_NET_USERNAME", "env-user")
    monkeypatch.setenv("FUDAN_NET_PASSWORD", "env-secret")
    monkeypatch.setenv("FUDAN_NET_INTERVAL", "5")

    config = load_config(
        load_dotenv_file=False,
        user_settings=UserSettings(username="settings-user", interval=20),
        credential_store=MemoryCredentials("credential-secret"),
    )

    assert config.username == "settings-user"
    assert config.password == "credential-secret"
    assert config.interval == 20


def test_missing_credentials_mentions_credential_store_when_settings_user_has_no_password(monkeypatch):
    monkeypatch.delenv("FUDAN_NET_USERNAME", raising=False)
    monkeypatch.delenv("FUDAN_NET_PASSWORD", raising=False)

    with pytest.raises(ConfigError) as excinfo:
        load_config(
            load_dotenv_file=False,
            user_settings=UserSettings(username="settings-user"),
            credential_store=MemoryCredentials(""),
        )

    assert "Windows Credential Manager" in str(excinfo.value)


def test_json_settings_store_round_trips_non_sensitive_settings(tmp_path):
    path = tmp_path / "config.json"
    store = JsonSettingsStore(path)

    store.save(
        UserSettings(
            username="test-user",
            base_url="http://portal.example",
            channel_name="campus",
            interval=30,
            check_timeout=2.5,
            check_urls=("https://one.example", "https://two.example"),
        )
    )

    assert "password" not in path.read_text(encoding="utf-8").lower()
    assert store.load() == UserSettings(
        username="test-user",
        base_url="http://portal.example",
        channel_name="campus",
        interval=30,
        check_timeout=2.5,
        check_urls=("https://one.example", "https://two.example"),
    )


def test_default_settings_path_uses_appdata(monkeypatch):
    monkeypatch.setenv("APPDATA", r"C:\Users\someone\AppData\Roaming")

    assert JsonSettingsStore.default_path() == Path(
        r"C:\Users\someone\AppData\Roaming\FudanWebTool\config.json"
    )
