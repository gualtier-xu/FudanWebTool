import json

import httpx
import pytest

from fudan_web_tool.portal import ChannelNotFoundError, PortalClient


def request_json(request):
    return json.loads(request.content.decode())


def make_client(handler):
    transport = httpx.MockTransport(handler)
    http_client = httpx.Client(transport=transport, base_url="http://10.102.250.36")
    return PortalClient(http_client), http_client


def test_pre_login_marks_online_state():
    def handler(request):
        assert request.url.path == "/api/v1/pre_login"
        assert request.method == "POST"
        assert request_json(request) == {
            "getuseronlinestate": "on_or_off",
            "user_ipadress": "10.102.122.161",
        }
        return httpx.Response(
            200,
            json={
                "code": 200,
                "message": "ok",
                "data": {"useronlinestate": "on", "username": "test-user"},
            },
        )

    portal, http_client = make_client(handler)
    try:
        status = portal.get_auth_status("10.102.122.161")
    finally:
        http_client.close()

    assert status.is_online is True
    assert status.raw["username"] == "test-user"


def test_pre_login_decodes_gbk_json_response():
    def handler(request):
        content = (
            '{"code":200,"data":{"useronlinestate":"off","text":"\u7528\u6237\u79bb\u7ebf"}}'
        ).encode("gbk")
        return httpx.Response(
            200,
            content=content,
            headers={"Content-Type": "application/json;charset=gbk"},
        )

    portal, http_client = make_client(handler)
    try:
        status = portal.get_auth_status("10.102.122.161")
    finally:
        http_client.close()

    assert status.is_online is False
    assert status.raw["text"] == "\u7528\u6237\u79bb\u7ebf"


def test_login_uses_firstauth_then_campus_channel():
    requests = []

    def handler(request):
        requests.append(request)
        body = request_json(request)
        if len(requests) == 1:
            assert request.url.path == "/api/v1/login"
            assert body["username"] == "test-user"
            assert body["password"] == "secret"
            assert body["ifautologin"] == "0"
            assert body["channel"] == "_GET"
            assert body["pagesign"] == "firstauth"
            assert body["usripadd"] == "10.102.122.161"
            return httpx.Response(
                200,
                json={
                    "code": 200,
                    "data": {
                        "channels": [
                            {"id": "cmcc", "name": "\u4e2d\u56fd\u79fb\u52a8"},
                            {"id": "campus", "name": "\u6821\u56ed\u7f51"},
                        ]
                    },
                },
            )

        assert body["channel"] == "campus"
        assert body["pagesign"] == "secondauth"
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {
                    "username": "test-user",
                    "outport": "\u6821\u56ed\u7f51",
                    "ip": "10.102.122.161",
                },
            },
        )

    portal, http_client = make_client(handler)
    try:
        result = portal.login(
            username="test-user",
            password="secret",
            ip_address="10.102.122.161",
            channel_name="\u6821\u56ed\u7f51",
        )
    finally:
        http_client.close()

    assert result.success is True
    assert result.data["outport"] == "\u6821\u56ed\u7f51"
    assert len(requests) == 2


def test_login_raises_when_campus_channel_missing():
    def handler(request):
        return httpx.Response(
            200,
            json={
                "code": 200,
                "data": {"channels": [{"id": "unicom", "name": "\u4e2d\u56fd\u8054\u901a"}]},
            },
        )

    portal, http_client = make_client(handler)
    try:
        with pytest.raises(ChannelNotFoundError):
            portal.login("u", "p", "10.102.122.161", "\u6821\u56ed\u7f51")
    finally:
        http_client.close()


def test_logout_uses_thirddauth_payload_without_real_password():
    def handler(request):
        assert request.url.path == "/api/v1/login"
        assert request_json(request) == {
            "username": "test-user",
            "password": "123",
            "channel": "0",
            "ifautologin": "1",
            "pagesign": "thirddauth",
            "usripadd": "10.102.122.161",
        }
        return httpx.Response(200, json={"code": 200, "data": {}})

    portal, http_client = make_client(handler)
    try:
        result = portal.logout("test-user", "10.102.122.161")
    finally:
        http_client.close()

    assert result.success is True
