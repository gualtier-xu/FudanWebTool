"""User settings and credential storage for the tray application."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
from typing import Protocol


APP_NAME = "FudanWebTool"
CONFIG_FILENAME = "config.json"
CREDENTIAL_SERVICE = "FudanWebTool"


@dataclass(frozen=True)
class UserSettings:
    username: str | None = None
    base_url: str | None = None
    channel_name: str | None = None
    interval: int | None = None
    check_timeout: float | None = None
    check_urls: tuple[str, ...] | None = None


class CredentialStore(Protocol):
    def get_password(self, username: str) -> str:
        """Return the saved password for a username, or an empty string."""

    def set_password(self, username: str, password: str) -> None:
        """Persist a password for a username."""


class WindowsCredentialStore:
    """Credential store backed by the active keyring provider."""

    def __init__(self, service_name: str = CREDENTIAL_SERVICE):
        self.service_name = service_name

    def get_password(self, username: str) -> str:
        if not username:
            return ""
        keyring = self._keyring()
        return keyring.get_password(self.service_name, username) or ""

    def set_password(self, username: str, password: str) -> None:
        if not username:
            raise ValueError("username is required to save a password")
        keyring = self._keyring()
        keyring.set_password(self.service_name, username, password)

    @staticmethod
    def _keyring():
        import keyring

        return keyring


class JsonSettingsStore:
    def __init__(self, path: Path):
        self.path = path

    @classmethod
    def default(cls) -> "JsonSettingsStore":
        return cls(cls.default_path())

    @staticmethod
    def default_path() -> Path:
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / APP_NAME / CONFIG_FILENAME
        try:
            from platformdirs import user_config_path
        except ImportError:
            return Path.home() / ".config" / APP_NAME / CONFIG_FILENAME
        return user_config_path(APP_NAME, appauthor=False) / CONFIG_FILENAME

    def load(self) -> UserSettings:
        if not self.path.exists():
            return UserSettings()
        data = json.loads(self.path.read_text(encoding="utf-8"))
        check_urls = data.get("check_urls")
        if isinstance(check_urls, list):
            data["check_urls"] = tuple(str(url) for url in check_urls if str(url).strip())
        else:
            data.pop("check_urls", None)
        allowed = {field.name for field in UserSettings.__dataclass_fields__.values()}
        return UserSettings(**{key: value for key, value in data.items() if key in allowed})

    def save(self, settings: UserSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            key: value
            for key, value in asdict(settings).items()
            if value is not None
        }
        if isinstance(settings.check_urls, tuple):
            data["check_urls"] = list(settings.check_urls)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
