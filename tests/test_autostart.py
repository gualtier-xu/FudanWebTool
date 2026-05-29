from pathlib import Path

from fudan_web_tool.autostart import StartupAutostart


def test_autostart_enable_creates_current_user_startup_script(tmp_path):
    autostart = StartupAutostart(startup_dir=tmp_path, command=["pythonw.exe", "-m", "fudan_web_tool", "tray"])

    autostart.enable()

    script = tmp_path / "FudanWebTool.cmd"
    assert script.exists()
    content = script.read_text(encoding="utf-8")
    assert "pythonw.exe" in content
    assert "-m fudan_web_tool tray" in content


def test_autostart_quotes_windows_paths_with_spaces(tmp_path):
    autostart = StartupAutostart(
        startup_dir=tmp_path,
        command=[r"C:\Program Files\Python\pythonw.exe", "-m", "fudan_web_tool", "tray"],
    )

    autostart.enable()

    assert '"C:\\Program Files\\Python\\pythonw.exe"' in (tmp_path / "FudanWebTool.cmd").read_text(encoding="utf-8")


def test_autostart_disable_removes_startup_script(tmp_path):
    script = tmp_path / "FudanWebTool.cmd"
    script.write_text("old", encoding="utf-8")
    autostart = StartupAutostart(startup_dir=tmp_path, command=["pythonw.exe", "-m", "fudan_web_tool", "tray"])

    autostart.disable()

    assert not script.exists()


def test_autostart_reports_enabled_from_startup_script(tmp_path):
    autostart = StartupAutostart(startup_dir=tmp_path, command=["pythonw.exe", "-m", "fudan_web_tool", "tray"])

    assert autostart.is_enabled() is False
    autostart.enable()
    assert autostart.is_enabled() is True


def test_default_startup_dir_uses_appdata(monkeypatch):
    monkeypatch.setenv("APPDATA", r"C:\Users\someone\AppData\Roaming")

    assert StartupAutostart.default_startup_dir() == Path(
        r"C:\Users\someone\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
    )
