"""Network traffic sampling and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import os
from pathlib import Path
import threading

from .settings import APP_NAME


TRAFFIC_FILENAME = "traffic.json"
VIRTUAL_NAME_MARKERS = ("loopback", "virtual", "vethernet", "vmware", "virtualbox", "pseudo-interface")


@dataclass(frozen=True)
class InterfaceCounters:
    bytes_sent: int
    bytes_recv: int


@dataclass(frozen=True)
class TrafficSnapshot:
    interface_name: str
    upload_bytes_per_second: int
    download_bytes_per_second: int
    today_upload_bytes: int
    today_download_bytes: int
    month_upload_bytes: int
    month_download_bytes: int
    is_available: bool = True

    @classmethod
    def unavailable(cls) -> "TrafficSnapshot":
        return cls("", 0, 0, 0, 0, 0, 0, False)

    @property
    def today_total_bytes(self) -> int:
        return self.today_upload_bytes + self.today_download_bytes

    @property
    def month_total_bytes(self) -> int:
        return self.month_upload_bytes + self.month_download_bytes


class JsonTrafficStore:
    def __init__(self, path: Path):
        self.path = path

    @classmethod
    def default(cls) -> "JsonTrafficStore":
        return cls(cls.default_path())

    @staticmethod
    def default_path() -> Path:
        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / APP_NAME / TRAFFIC_FILENAME
        return Path.home() / ".config" / APP_NAME / TRAFFIC_FILENAME

    def add_usage(self, day: date, *, upload_bytes: int, download_bytes: int) -> None:
        data = self._load_data()
        key = day.isoformat()
        entry = data.setdefault("daily", {}).setdefault(key, {"upload": 0, "download": 0})
        entry["upload"] = int(entry.get("upload", 0)) + max(0, int(upload_bytes))
        entry["download"] = int(entry.get("download", 0)) + max(0, int(download_bytes))
        self._save_data(data)

    def daily_total(self, day: date) -> tuple[int, int]:
        entry = self._load_data().get("daily", {}).get(day.isoformat(), {})
        return int(entry.get("upload", 0)), int(entry.get("download", 0))

    def month_total(self, day: date) -> tuple[int, int]:
        prefix = f"{day.year:04d}-{day.month:02d}-"
        upload = 0
        download = 0
        for key, entry in self._load_data().get("daily", {}).items():
            if key.startswith(prefix):
                upload += int(entry.get("upload", 0))
                download += int(entry.get("download", 0))
        return upload, download

    def _load_data(self) -> dict:
        if not self.path.exists():
            return {"daily": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def _save_data(self, data: dict) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


class TrafficSampler:
    def __init__(self, store: JsonTrafficStore, now=date.today):
        self.store = store
        self.now = now
        self._previous_name: str | None = None
        self._previous: InterfaceCounters | None = None
        self._snapshot = TrafficSnapshot.unavailable()
        self._lock = threading.Lock()

    @property
    def snapshot(self) -> TrafficSnapshot:
        with self._lock:
            return self._snapshot

    def sample(self, counters: dict[str, InterfaceCounters], elapsed_seconds: float) -> TrafficSnapshot:
        interface = select_active_interface(counters)
        if interface is None:
            snapshot = TrafficSnapshot.unavailable()
            with self._lock:
                self._snapshot = snapshot
            return snapshot

        current = counters[interface]
        upload_delta = 0
        download_delta = 0
        if self._previous is not None and self._previous_name == interface:
            upload_delta = max(0, current.bytes_sent - self._previous.bytes_sent)
            download_delta = max(0, current.bytes_recv - self._previous.bytes_recv)
        self._previous_name = interface
        self._previous = current

        day = self.now()
        self.store.add_usage(day, upload_bytes=upload_delta, download_bytes=download_delta)
        today_upload, today_download = self.store.daily_total(day)
        month_upload, month_download = self.store.month_total(day)
        elapsed = max(elapsed_seconds, 0.001)
        snapshot = TrafficSnapshot(
            interface_name=interface,
            upload_bytes_per_second=int(upload_delta / elapsed),
            download_bytes_per_second=int(download_delta / elapsed),
            today_upload_bytes=today_upload,
            today_download_bytes=today_download,
            month_upload_bytes=month_upload,
            month_download_bytes=month_download,
        )
        with self._lock:
            self._snapshot = snapshot
        return snapshot

    def sample_current(self, elapsed_seconds: float) -> TrafficSnapshot:
        return self.sample(read_interface_counters(), elapsed_seconds)


def read_interface_counters() -> dict[str, InterfaceCounters]:
    import psutil

    counters = psutil.net_io_counters(pernic=True)
    return {
        name: InterfaceCounters(bytes_sent=value.bytes_sent, bytes_recv=value.bytes_recv)
        for name, value in counters.items()
    }


def select_active_interface(counters: dict[str, InterfaceCounters]) -> str | None:
    candidates = [
        (name, value.bytes_sent + value.bytes_recv)
        for name, value in counters.items()
        if value.bytes_sent + value.bytes_recv > 0 and not _is_ignored_interface(name)
    ]
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[1], reverse=True)
    return candidates[0][0]


def _is_ignored_interface(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in VIRTUAL_NAME_MARKERS)


def format_bytes(value: int) -> str:
    amount = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if amount < 1024 or unit == "TB":
            if unit == "B":
                return f"{int(amount)} B"
            return f"{amount:.1f} {unit}"
        amount /= 1024
