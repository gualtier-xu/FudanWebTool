import logging
import sys

from fudan_web_tool import cli


def test_build_parser_exposes_status_once_and_watch():
    parser = cli.build_parser()

    assert parser.parse_args(["status"]).command == "status"
    assert parser.parse_args(["once"]).command == "once"
    assert parser.parse_args(["watch"]).command == "watch"
    assert parser.parse_args(["tray"]).command == "tray"
    assert parser.parse_args(["tray", "--foreground"]).foreground is True


def test_tray_command_launches_detached_background_process(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "launch_detached_tray_app", lambda: calls.append("detached") or 0)

    assert cli.main(["tray"]) == 0
    assert calls == ["detached"]


def test_tray_foreground_command_runs_tray_application(monkeypatch):
    calls = []

    monkeypatch.setattr(cli, "run_tray_app", lambda: calls.append("foreground") or 0)

    assert cli.main(["tray", "--foreground"]) == 0
    assert calls == ["foreground"]


def test_tray_command_reports_missing_gui_dependency(monkeypatch, capsys):
    def missing_dependency():
        raise ModuleNotFoundError("No module named 'PySide6'")

    monkeypatch.setattr(cli, "run_tray_app", missing_dependency)

    assert cli.main(["tray", "--foreground"]) == 2
    assert "PySide6 is not installed" in capsys.readouterr().err


def test_detached_tray_launcher_uses_pythonw_when_available(monkeypatch):
    calls = []

    monkeypatch.setattr(cli.sys, "executable", r"C:\Env\python.exe")
    monkeypatch.setattr(cli, "_existing_pythonw", lambda executable: r"C:\Env\pythonw.exe")
    monkeypatch.setattr(cli.subprocess, "Popen", lambda command, **kwargs: calls.append((command, kwargs)))

    assert cli.launch_detached_tray_app() == 0

    command, kwargs = calls[0]
    assert command == [r"C:\Env\pythonw.exe", "-m", "fudan_web_tool", "tray", "--foreground"]
    assert kwargs["cwd"] is None


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
