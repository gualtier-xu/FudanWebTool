"""Command-line interface for FudanWebTool."""

from __future__ import annotations

import argparse
import logging
import sys
import time

from .config import ConfigError, load_config
from .connectivity import ConnectivityChecker
from .portal import PortalClient
from .recovery import RecoveryManager


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="fudan-web-tool")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("status", help="check connectivity and portal status without logging in")
    subparsers.add_parser("once", help="run one recovery attempt")
    subparsers.add_parser("watch", help="keep monitoring and recover when disconnected")
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)
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
    while True:
        result = manager.run_once()
        logging.info("%s: %s; next check in %s seconds", result.action, result.message, interval)
        time.sleep(interval)


if __name__ == "__main__":
    raise SystemExit(main())
