"""Application configuration loaded from local environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv

from .settings import CredentialStore, UserSettings


DEFAULT_BASE_URL = "http://10.102.250.36"
DEFAULT_CHANNEL_NAME = "\u6821\u56ed\u7f51"
DEFAULT_INTERVAL = 5
DEFAULT_CHECK_TIMEOUT = 3.0
DEFAULT_CHECK_URLS = (
    "http://connect.rom.miui.com/generate_204",
    "https://www.baidu.com",
    "https://www.qq.com",
)


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class AppConfig:
    username: str
    password: str
    base_url: str
    channel_name: str
    interval: int
    check_timeout: float
    check_urls: tuple[str, ...]


def load_config(
    *,
    load_dotenv_file: bool = True,
    require_credentials: bool = True,
    user_settings: UserSettings | None = None,
    credential_store: CredentialStore | None = None,
) -> AppConfig:
    if load_dotenv_file:
        load_dotenv()

    user_settings = user_settings or UserSettings()
    username = _setting_or_env(user_settings.username, "FUDAN_NET_USERNAME", "").strip()
    env_password = os.getenv("FUDAN_NET_PASSWORD", "")
    password = ""
    if credential_store is not None and username:
        password = credential_store.get_password(username)
    if not password:
        password = env_password
    missing = [
        name
        for name, value in (
            ("FUDAN_NET_USERNAME", username),
            ("Windows Credential Manager password or FUDAN_NET_PASSWORD", password),
        )
        if not value
    ]
    if require_credentials and missing:
        raise ConfigError("Missing required configuration: " + ", ".join(missing))

    interval_text = str(_setting_or_env(user_settings.interval, "FUDAN_NET_INTERVAL", DEFAULT_INTERVAL)).strip()
    try:
        interval = int(interval_text)
    except ValueError as exc:
        raise ConfigError("FUDAN_NET_INTERVAL must be an integer") from exc
    if interval <= 0:
        raise ConfigError("FUDAN_NET_INTERVAL must be greater than 0")

    timeout_text = str(
        _setting_or_env(user_settings.check_timeout, "FUDAN_NET_CHECK_TIMEOUT", DEFAULT_CHECK_TIMEOUT)
    ).strip()
    try:
        check_timeout = float(timeout_text)
    except ValueError as exc:
        raise ConfigError("FUDAN_NET_CHECK_TIMEOUT must be a number") from exc
    if check_timeout <= 0:
        raise ConfigError("FUDAN_NET_CHECK_TIMEOUT must be greater than 0")

    if user_settings.check_urls is not None:
        urls = tuple(part.strip() for part in user_settings.check_urls if part.strip())
    else:
        urls = tuple(
            part.strip()
            for part in os.getenv("FUDAN_NET_CHECK_URLS", ",".join(DEFAULT_CHECK_URLS)).split(",")
            if part.strip()
        )
    if not urls:
        raise ConfigError("FUDAN_NET_CHECK_URLS must contain at least one URL")

    return AppConfig(
        username=username,
        password=password,
        base_url=_setting_or_env(user_settings.base_url, "FUDAN_NET_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/"),
        channel_name=_setting_or_env(
            user_settings.channel_name,
            "FUDAN_NET_CHANNEL_NAME",
            DEFAULT_CHANNEL_NAME,
        ).strip(),
        interval=interval,
        check_timeout=check_timeout,
        check_urls=urls,
    )


def _setting_or_env(value, env_name: str, default):
    if value is not None:
        return value
    return os.getenv(env_name, default)
