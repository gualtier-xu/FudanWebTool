import tomllib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_exposes_console_script():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["scripts"]["fudan-web-tool"] == "fudan_web_tool.cli:main"


def test_env_file_is_ignored_and_example_has_no_secrets():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert ".env" in gitignore
    assert "FUDAN_NET_PASSWORD=" in env_example
    assert "secret" not in env_example.lower()


def test_pyproject_declares_tray_and_packaging_dependencies():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "PySide6>=6.7" in data["project"]["dependencies"]
    assert "keyring>=25.0" in data["project"]["dependencies"]
    assert "platformdirs>=4.0" in data["project"]["dependencies"]
    assert "psutil>=5.9" in data["project"]["dependencies"]
    assert "pyinstaller>=6.0" in data["project"]["optional-dependencies"]["build"]


def test_windows_packaging_files_exist():
    assert (ROOT / "fudan-web-tool-tray.spec").exists()
    assert (ROOT / "scripts" / "build-windows.ps1").exists()


def test_tray_icon_is_packaged():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    spec = (ROOT / "fudan-web-tool-tray.spec").read_text(encoding="utf-8")

    assert (ROOT / "src" / "fudan_web_tool" / "assets" / "tray_icon.png").exists()
    assert data["tool"]["setuptools"]["package-data"]["fudan_web_tool"] == ["assets/tray_icon.png"]
    assert "collect_data_files(\"fudan_web_tool\")" in spec
