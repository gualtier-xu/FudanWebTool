"""Command-line interface for FudanWebTool."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
import subprocess
import sys
import time

from .config import ConfigError, load_config
from .connectivity import ConnectivityChecker
from .monitor import BackgroundMonitor
from .portal import PortalClient
from .recovery import RecoveryManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fudan-web-tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="check connectivity and portal status without logging in")
    subparsers.add_parser("once", help="run one recovery attempt")
    subparsers.add_parser("watch", help="keep monitoring and recover when disconnected")
    tray_parser = subparsers.add_parser("tray", help="run as a Windows system tray application")
    tray_parser.add_argument(
        "--foreground",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
    if args.command == "tray":
        if not args.foreground:
            return launch_detached_tray_app()
        try:
            return run_tray_app()
        except ModuleNotFoundError as exc:
            if exc.name == "PySide6" or "PySide6" in str(exc):
                print(
                    "PySide6 is not installed in this Python environment. "
                    "Update the fudan-web-tool environment before running the tray app.",
                    file=sys.stderr,
                )
                return 2
            raise
    try:
        config = load_config(require_credentials=args.command != "status")
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2

    portal = PortalClient.create(config.base_url)
    connectivity = ConnectivityChecker(config.check_urls, timeout=config.check_timeout)
    try:
        if args.command == "status":
            return _status(portal, connectivity)
        manager = RecoveryManager(config, portal, connectivity)
        if args.command == "once":
            result = manager.run_once()
            print(f"{result.action}: {result.message}")
            return 0
        if args.command == "watch":
            return _watch(manager, config.interval)
    finally:
        connectivity.close()
        portal.close()
    return 1


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
        force=True,
    )


def _status(portal: PortalClient, connectivity: ConnectivityChecker) -> int:
    result = connectivity.check()
    ip_address = portal.get_ip()
    status = portal.get_auth_status(ip_address)
    print(f"IP: {ip_address}")
    print(f"External network: {'online' if result.is_online else 'offline'}")
    print(f"Portal status: {'online' if status.is_online else 'offline'}")
    return 0


def _watch(manager: RecoveryManager, interval: int) -> int:
    monitor = BackgroundMonitor(manager, interval)
    while True:
        result = monitor.run_cycle_if_active()
        logging.info("%s: %s; next check in %s seconds", result.action, result.message, interval)
        time.sleep(interval)


def run_tray_app() -> int:
    from .tray_app import run_tray_app as run

    return run()


def launch_detached_tray_app() -> int:
    executable = _existing_pythonw(sys.executable) or sys.executable
    creationflags = 0
    startupinfo = None
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.DETACHED_PROCESS
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = 0

    subprocess.Popen(
        [executable, "-m", "fudan_web_tool", "tray", "--foreground"],
        cwd=None,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        creationflags=creationflags,
        startupinfo=startupinfo,
    )
    print("FudanWebTool tray is running in the background.")
    return 0


def _existing_pythonw(executable: str) -> str | None:
    path = Path(executable)
    if path.name.lower() != "python.exe":
        return None
    pythonw = path.with_name("pythonw.exe")
    if pythonw.exists():
        return str(pythonw)
    return None


if __name__ == "__main__":
    raise SystemExit(main())
