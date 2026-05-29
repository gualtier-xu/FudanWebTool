"""PyInstaller entry point for the tray-only Windows executable."""

from __future__ import annotations

from fudan_web_tool.cli import configure_logging
from fudan_web_tool.tray_app import run_tray_app


def main() -> int:
    configure_logging()
    return run_tray_app()


if __name__ == "__main__":
    raise SystemExit(main())
