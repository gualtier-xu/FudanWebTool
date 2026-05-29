"""Application configuration loaded from local environment variables."""

from __future__ import annotations

from dataclasses import dataclass
import os

from dotenv import load_dotenv


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


def load_config(*, load_dotenv_file: bool = True, require_credentials: bool = True) -> AppConfig:
    if load_dotenv_file:
        load_dotenv()

    username = os.getenv("FUDAN_NET_USERNAME", "").strip()
    password = os.getenv("FUDAN_NET_PASSWORD", "")
    missing = [
        name
        for name, value in (
            ("FUDAN_NET_USERNAME", username),
            ("FUDAN_NET_PASSWORD", password),
        )
        if not value
    ]
    if require_credentials and missing:
        raise ConfigError("Missing required configuration: " + ", ".join(missing))

    interval_text = os.getenv("FUDAN_NET_INTERVAL", str(DEFAULT_INTERVAL)).strip()
    try:
        interval = int(interval_text)
    except ValueError as exc:
        raise ConfigError("FUDAN_NET_INTERVAL must be an integer") from exc
    if interval <= 0:
        raise ConfigError("FUDAN_NET_INTERVAL must be greater than 0")

    timeout_text = os.getenv("FUDAN_NET_CHECK_TIMEOUT", str(DEFAULT_CHECK_TIMEOUT)).strip()
    try:
        check_timeout = float(timeout_text)
    except ValueError as exc:
        raise ConfigError("FUDAN_NET_CHECK_TIMEOUT must be a number") from exc
    if check_timeout <= 0:
        raise ConfigError("FUDAN_NET_CHECK_TIMEOUT must be greater than 0")

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
        base_url=os.getenv("FUDAN_NET_BASE_URL", DEFAULT_BASE_URL).strip().rstrip("/"),
        channel_name=os.getenv("FUDAN_NET_CHANNEL_NAME", DEFAULT_CHANNEL_NAME).strip(),
        interval=interval,
        check_timeout=check_timeout,
        check_urls=urls,
    )
