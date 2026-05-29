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
