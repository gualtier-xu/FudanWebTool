import logging
import sys

from fudan_web_tool import cli


def test_build_parser_exposes_status_once_and_watch():
    parser = cli.build_parser()

    assert parser.parse_args(["status"]).command == "status"
    assert parser.parse_args(["once"]).command == "once"
    assert parser.parse_args(["watch"]).command == "watch"


def test_status_loads_config_without_requiring_credentials(monkeypatch):
    calls = {}

    def fake_load_config(**kwargs):
        calls.update(kwargs)
        raise cli.ConfigError("stop before network")

    monkeypatch.setattr(cli, "load_config", fake_load_config)

    assert cli.main(["status"]) == 2
    assert calls["require_credentials"] is False


def test_configure_logging_sends_logs_to_stdout(monkeypatch):
    captured = {}

    def fake_basic_config(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(logging, "basicConfig", fake_basic_config)

    cli.configure_logging()

    assert captured["stream"] is sys.stdout
