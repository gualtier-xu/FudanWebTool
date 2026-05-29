"""Current-user Windows startup integration."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


APP_NAME = "FudanWebTool"
STARTUP_SCRIPT = f"{APP_NAME}.cmd"


class StartupAutostart:
    def __init__(self, startup_dir: Path | None = None, command: list[str] | None = None):
        self.startup_dir = startup_dir or self.default_startup_dir()
        self.command = command or self.default_command()

    @staticmethod
    def default_startup_dir() -> Path:
        appdata = os.getenv("APPDATA")
        if not appdata:
            return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
        return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"

    @staticmethod
    def default_command() -> list[str]:
        executable = Path(sys.executable)
        if executable.name.lower() == "python.exe":
            pythonw = executable.with_name("pythonw.exe")
            if pythonw.exists():
                executable = pythonw
        return [str(executable), "-m", "fudan_web_tool", "tray"]

    @property
    def script_path(self) -> Path:
        return self.startup_dir / STARTUP_SCRIPT

    def is_enabled(self) -> bool:
        return self.script_path.exists()

    def enable(self) -> None:
        self.startup_dir.mkdir(parents=True, exist_ok=True)
        self.script_path.write_text(self._script_content(), encoding="utf-8")

    def disable(self) -> None:
        if self.script_path.exists():
            self.script_path.unlink()

    def _script_content(self) -> str:
        command = subprocess.list2cmdline(self.command)
        return f"@echo off\r\nstart \"\" {command}\r\n"
