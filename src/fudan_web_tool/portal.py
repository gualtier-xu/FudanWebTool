"""HTTP client for the Fudan campus network portal."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any

import httpx


GBK_JSON_HEADERS = {
    "Content-Type": "application/json;charset=gbk",
    "Access-Control-Allow-Origin": "*",
}

ERROR_MESSAGES = {
    "E2531": "User not found. 用户不存在",
    "E2532": "The two authentication interval cannot be less than 30 seconds. 两次认证间隔太短",
    "E2533": "Too many attempts. 请 5 分钟后再试",
    "E2534": "Proxy behavior detected. 有代理行为被禁用",
    "E2553": "Password is error. 密码错误",
    "E2606": "User is disabled. 用户被禁用",
    "E2616": "Arrearage users. 用户已欠费",
    "E2620": "User is already online. 已经在线了",
    "E2621": "The number of online users reached the licensing number. 已达到授权人数",
    "E2901": "认证失败，校园网账号或密码错误",
}


class PortalError(RuntimeError):
    """Raised when the campus portal returns an invalid or failed response."""


class ChannelNotFoundError(PortalError):
    """Raised when the configured network channel is not in the portal response."""


@dataclass(frozen=True)
class AuthStatus:
    is_online: bool
    raw: dict[str, Any]


@dataclass(frozen=True)
class LoginResult:
    success: bool
    message: str
    data: dict[str, Any]


class PortalClient:
    def __init__(self, client: httpx.Client):
        self.client = client

    @classmethod
    def create(cls, base_url: str, *, timeout: float = 10.0) -> "PortalClient":
        return cls(
            httpx.Client(
                base_url=base_url.rstrip("/"),
                timeout=timeout,
                headers={"Content-Type": "application/json"},
                trust_env=False,
            )
        )

    def close(self) -> None:
        self.client.close()

    def get_ip(self) -> str:
        payload = self._request("GET", "/api/v1/ip")
        ip_address = payload.get("data")
        if not isinstance(ip_address, str) or not ip_address:
            raise PortalError("Portal did not return a valid IP address")
        return ip_address

    def get_auth_status(self, ip_address: str) -> AuthStatus:
        payload = self._request(
            "POST",
            "/api/v1/pre_login",
            json={"getuseronlinestate": "on_or_off", "user_ipadress": ip_address},
            headers=GBK_JSON_HEADERS,
        )
        data = self._data_dict(payload)
        return AuthStatus(is_online=data.get("useronlinestate") == "on", raw=data)

    def login(
        self,
        username: str,
        password: str,
        ip_address: str,
        channel_name: str,
    ) -> LoginResult:
        first = self._login_request(
            username=username,
            password=password,
            ip_address=ip_address,
            channel="_GET",
            pagesign="firstauth",
            ifautologin="0",
        )
        channels = first.data.get("channels")
        if not channels:
            return first

        channel_id = self._find_channel_id(channels, channel_name)
        return self._login_request(
            username=username,
            password=password,
            ip_address=ip_address,
            channel=channel_id,
            pagesign="secondauth",
            ifautologin="0",
        )

    def logout(self, username: str, ip_address: str) -> LoginResult:
        return self._login_request(
            username=username,
            password="123",
            ip_address=ip_address,
            channel="0",
            pagesign="thirddauth",
            ifautologin="1",
        )

    def _login_request(
        self,
        *,
        username: str,
        password: str,
        ip_address: str,
        channel: str,
        pagesign: str,
        ifautologin: str,
    ) -> LoginResult:
        payload = self._request(
            "POST",
            "/api/v1/login",
            json={
                "username": username,
                "password": password,
                "ifautologin": ifautologin,
                "channel": channel,
                "pagesign": pagesign,
                "usripadd": ip_address,
            },
            headers=GBK_JSON_HEADERS,
        )
        data = self._data_dict(payload)
        return LoginResult(
            success=payload.get("code") == 200,
            message=self._message_for(data),
            data=data,
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = self.client.request(method, path, **kwargs)
        response.raise_for_status()
        payload = self._decode_json(response)
        if not isinstance(payload, dict):
            raise PortalError("Portal returned a non-object response")
        if payload.get("code") != 200:
            data = payload.get("data")
            if isinstance(data, dict):
                text = str(data.get("text", payload.get("message", "Portal request failed")))
            else:
                text = str(data or payload.get("message", "Portal request failed"))
            raise PortalError(ERROR_MESSAGES.get(text, text))
        return payload

    @staticmethod
    def _decode_json(response: httpx.Response) -> Any:
        try:
            return response.json()
        except UnicodeDecodeError:
            content_type = response.headers.get("content-type", "").lower()
            encoding = "gbk" if "gbk" in content_type else "gb18030"
            return json.loads(response.content.decode(encoding))

    @staticmethod
    def _data_dict(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data")
        if isinstance(data, dict):
            return data
        return {}

    @staticmethod
    def _message_for(data: dict[str, Any]) -> str:
        text = str(data.get("text", "ok"))
        return ERROR_MESSAGES.get(text, text)

    @staticmethod
    def _find_channel_id(channels: Any, channel_name: str) -> str:
        if not isinstance(channels, list):
            raise ChannelNotFoundError("Portal returned an invalid channel list")
        for channel in channels:
            if isinstance(channel, dict) and channel.get("name") == channel_name:
                channel_id = channel.get("id")
                if channel_id is not None:
                    return str(channel_id)
        names = [
            str(channel.get("name"))
            for channel in channels
            if isinstance(channel, dict) and channel.get("name")
        ]
        raise ChannelNotFoundError(
            f"Channel {channel_name!r} not found. Available channels: {', '.join(names)}"
        )
