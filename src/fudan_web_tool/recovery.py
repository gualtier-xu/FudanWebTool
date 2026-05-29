"""Recovery orchestration for connectivity and portal authentication."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from .config import AppConfig


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class RecoveryResult:
    action: str
    message: str


class RecoveryManager:
    def __init__(self, config: AppConfig, portal, connectivity):
        self.config = config
        self.portal = portal
        self.connectivity = connectivity

    def run_once(self) -> RecoveryResult:
        LOGGER.info("Starting one recovery cycle")
        LOGGER.info("Checking external network connectivity")
        connectivity = self.connectivity.check()
        if connectivity.is_online:
            LOGGER.info("External network is reachable via %s", connectivity.successful_url)
            return RecoveryResult("already_online", "External network is reachable")

        LOGGER.warning("External network is offline; checking portal status")
        LOGGER.info("Fetching portal IP address")
        ip_address = self.portal.get_ip()
        LOGGER.info("Portal IP address: %s", ip_address)
        LOGGER.info("Checking portal auth state for %s", ip_address)
        status = self.portal.get_auth_status(ip_address)
        LOGGER.info("Portal auth state: %s", "online" if status.is_online else "offline")
        if status.is_online:
            LOGGER.warning("False-online state detected; logging out before reconnecting")
            self.portal.logout(self.config.username, ip_address)
            LOGGER.info("Logout request completed")
            action = "relogin"
        else:
            LOGGER.info("Portal reports offline; login can start directly")
            action = "login"

        LOGGER.info("Starting login request for channel %s", self.config.channel_name)
        result = self.portal.login(
            self.config.username,
            self.config.password,
            ip_address,
            self.config.channel_name,
        )
        if not result.success:
            LOGGER.error("Login request failed: %s", result.message)
            return RecoveryResult(action, result.message)
        LOGGER.info("Login request completed for channel %s", self.config.channel_name)
        return RecoveryResult(action, "Login request completed")
