"""Background monitoring controller shared by CLI and tray UI."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import threading


LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class MonitorStatus:
    is_running: bool = False
    is_paused: bool = False
    last_action: str = ""
    last_message: str = ""
    last_error: str = ""


class BackgroundMonitor:
    def __init__(self, manager, interval: int, close_callback=None):
        self.manager = manager
        self.interval = interval
        self.close_callback = close_callback
        self._closed = False
        self._status = MonitorStatus()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def status(self) -> MonitorStatus:
        with self._lock:
            return self._status

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._status = MonitorStatus(is_running=True, is_paused=self._status.is_paused)
            self._thread = threading.Thread(target=self._run_loop, name="fudan-web-monitor", daemon=True)
            self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        thread = self._thread
        if thread and thread.is_alive() and thread is not threading.current_thread():
            thread.join(timeout=2)
        with self._lock:
            self._status = MonitorStatus(
                is_running=False,
                is_paused=self._status.is_paused,
                last_action=self._status.last_action,
                last_message=self._status.last_message,
                last_error=self._status.last_error,
            )
            if not self._closed and self.close_callback is not None:
                self.close_callback()
                self._closed = True

    def pause(self) -> None:
        with self._lock:
            self._status = MonitorStatus(
                is_running=self._status.is_running,
                is_paused=True,
                last_action=self._status.last_action,
                last_message=self._status.last_message,
                last_error=self._status.last_error,
            )

    def resume(self) -> None:
        with self._lock:
            self._status = MonitorStatus(
                is_running=self._status.is_running,
                is_paused=False,
                last_action=self._status.last_action,
                last_message=self._status.last_message,
                last_error=self._status.last_error,
            )

    def run_now(self):
        try:
            result = self.manager.run_once()
        except Exception as exc:
            LOGGER.exception("Background recovery cycle failed")
            with self._lock:
                self._status = MonitorStatus(
                    is_running=self._status.is_running,
                    is_paused=self._status.is_paused,
                    last_action=self._status.last_action,
                    last_message=self._status.last_message,
                    last_error=str(exc),
                )
            raise
        with self._lock:
            self._status = MonitorStatus(
                is_running=self._status.is_running,
                is_paused=self._status.is_paused,
                last_action=result.action,
                last_message=result.message,
                last_error="",
            )
        return result

    def run_cycle_if_active(self):
        if self.status.is_paused:
            return None
        return self.run_now()

    def _run_loop(self) -> None:
        while not self._stop_event.is_set():
            self.run_cycle_if_active()
            self._stop_event.wait(self.interval)
