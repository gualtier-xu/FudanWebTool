"""Windows system tray application."""

from __future__ import annotations

import logging

from .config import AppConfig, load_config
from .connectivity import ConnectivityChecker
from .monitor import BackgroundMonitor
from .portal import PortalClient
from .recovery import RecoveryManager
from .settings import JsonSettingsStore, UserSettings, WindowsCredentialStore


LOGGER = logging.getLogger(__name__)


class TrayActions:
    def __init__(self, monitor: BackgroundMonitor, open_settings, quit_app):
        self.monitor = monitor
        self._open_settings = open_settings
        self._quit_app = quit_app

    def status_text(self) -> str:
        status = self.monitor.status
        if status.last_error:
            return f"error: {status.last_error}"
        if status.last_action:
            return f"{status.last_action}: {status.last_message}"
        return "waiting for first check"

    def run_now(self) -> None:
        self.monitor.run_now()

    def toggle_pause(self) -> None:
        if self.monitor.status.is_paused:
            self.monitor.resume()
        else:
            self.monitor.pause()

    def open_settings(self) -> None:
        self._open_settings()

    def quit(self) -> None:
        self.monitor.stop()
        self._quit_app()


def create_monitor() -> BackgroundMonitor:
    settings_store = JsonSettingsStore.default()
    credentials = WindowsCredentialStore()
    settings = settings_store.load()
    config = load_config(user_settings=settings, credential_store=credentials)
    return monitor_from_config(config)


def monitor_from_config(config: AppConfig) -> BackgroundMonitor:
    portal = PortalClient.create(config.base_url)
    connectivity = ConnectivityChecker(config.check_urls, timeout=config.check_timeout)
    manager = RecoveryManager(config, portal, connectivity)
    return BackgroundMonitor(
        manager,
        config.interval,
        close_callback=lambda: (connectivity.close(), portal.close()),
    )


def run_tray_app() -> int:
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QAction, QIcon
    from PySide6.QtWidgets import (
        QApplication,
        QDialog,
        QFormLayout,
        QLineEdit,
        QMenu,
        QMessageBox,
        QPushButton,
        QSpinBox,
        QDoubleSpinBox,
        QStyle,
        QSystemTrayIcon,
        QVBoxLayout,
        QWidget,
    )

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)

    settings_store = JsonSettingsStore.default()
    credentials = WindowsCredentialStore()
    monitor = create_monitor()
    monitor.start()
    actions = TrayActions(monitor, lambda: None, app.quit)

    def restart_monitor() -> None:
        actions.monitor.stop()
        actions.monitor = create_monitor()
        actions.monitor.start()

    def open_settings() -> None:
        dialog = _build_settings_dialog(
            parent=None,
            settings_store=settings_store,
            credentials=credentials,
            restart_monitor=restart_monitor,
            widgets=(
                QDialog,
                QFormLayout,
                QLineEdit,
                QPushButton,
                QSpinBox,
                QDoubleSpinBox,
                QVBoxLayout,
                QMessageBox,
            ),
        )
        dialog.exec()

    tray = QSystemTrayIcon()
    icon = app.style().standardIcon(QStyle.StandardPixmap.SP_ComputerIcon)
    tray.setIcon(icon if not icon.isNull() else QIcon())
    tray.setToolTip("FudanWebTool")

    actions._open_settings = open_settings
    menu = QMenu()
    status_action = QAction(actions.status_text(), menu)
    status_action.setEnabled(False)
    check_action = QAction("Check now", menu)
    pause_action = QAction("Pause", menu)
    settings_action = QAction("Settings", menu)
    quit_action = QAction("Quit", menu)

    check_action.triggered.connect(actions.run_now)
    pause_action.triggered.connect(lambda: (actions.toggle_pause(), refresh_menu()))
    settings_action.triggered.connect(actions.open_settings)
    quit_action.triggered.connect(actions.quit)

    for action in (status_action, check_action, pause_action, settings_action, quit_action):
        menu.addAction(action)
    tray.setContextMenu(menu)

    def refresh_menu() -> None:
        status_action.setText(actions.status_text())
        pause_action.setText("Resume" if actions.monitor.status.is_paused else "Pause")

    timer = QTimer()
    timer.timeout.connect(refresh_menu)
    timer.start(1000)
    tray.show()
    return app.exec()


def _build_settings_dialog(parent, settings_store, credentials, restart_monitor, widgets):
    (
        QDialog,
        QFormLayout,
        QLineEdit,
        QPushButton,
        QSpinBox,
        QDoubleSpinBox,
        QVBoxLayout,
        QMessageBox,
    ) = widgets
    settings = settings_store.load()
    dialog = QDialog(parent)
    dialog.setWindowTitle("FudanWebTool Settings")

    username = QLineEdit(settings.username or "")
    password = QLineEdit("")
    password.setEchoMode(QLineEdit.EchoMode.Password)
    password.setPlaceholderText("Saved in Windows Credential Manager")
    base_url = QLineEdit(settings.base_url or "")
    channel_name = QLineEdit(settings.channel_name or "")
    interval = QSpinBox()
    interval.setRange(1, 86400)
    interval.setValue(settings.interval or 5)
    timeout = QDoubleSpinBox()
    timeout.setRange(0.1, 120.0)
    timeout.setSingleStep(0.5)
    timeout.setValue(settings.check_timeout or 3.0)
    check_urls = QLineEdit(", ".join(settings.check_urls or ()))

    form = QFormLayout()
    form.addRow("Username", username)
    form.addRow("Password", password)
    form.addRow("Portal URL", base_url)
    form.addRow("Channel", channel_name)
    form.addRow("Interval seconds", interval)
    form.addRow("Timeout seconds", timeout)
    form.addRow("Check URLs", check_urls)

    save = QPushButton("Save")

    def save_settings() -> None:
        parsed = UserSettings(
            username=username.text().strip() or None,
            base_url=base_url.text().strip() or None,
            channel_name=channel_name.text().strip() or None,
            interval=interval.value(),
            check_timeout=timeout.value(),
            check_urls=tuple(part.strip() for part in check_urls.text().split(",") if part.strip()) or None,
        )
        settings_store.save(parsed)
        if password.text():
            credentials.set_password(username.text().strip(), password.text())
        restart_monitor()
        QMessageBox.information(dialog, "FudanWebTool", "Settings saved. Restart the tray app to reload them.")
        dialog.accept()

    save.clicked.connect(save_settings)
    layout = QVBoxLayout()
    layout.addLayout(form)
    layout.addWidget(save)
    dialog.setLayout(layout)
    return dialog
