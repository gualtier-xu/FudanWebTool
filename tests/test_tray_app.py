from fudan_web_tool.settings import UserSettings
from fudan_web_tool.tray_app import TrayActions, apply_tray_settings, tray_icon_path
from fudan_web_tool.traffic import TrafficSnapshot


class FakeMonitor:
    def __init__(self):
        self.calls = []
        self.status = type(
            "MonitorStatus",
            (),
            {
                "is_paused": False,
                "last_action": "already_online",
                "last_message": "External network is reachable",
                "last_error": "",
            },
        )()

    def run_now(self):
        self.calls.append("run_now")

    def pause(self):
        self.calls.append("pause")
        self.status.is_paused = True

    def resume(self):
        self.calls.append("resume")
        self.status.is_paused = False

    def stop(self):
        self.calls.append("stop")


def test_tray_actions_toggle_pause_and_resume():
    monitor = FakeMonitor()
    actions = TrayActions(monitor, open_settings=lambda: None, quit_app=lambda: None)

    actions.toggle_pause()
    actions.toggle_pause()

    assert monitor.calls == ["pause", "resume"]


def test_tray_actions_format_status_and_invoke_commands():
    monitor = FakeMonitor()
    opened = []
    quit_calls = []
    actions = TrayActions(monitor, open_settings=lambda: opened.append(True), quit_app=lambda: quit_calls.append(True))

    assert actions.status_text() == "already_online: External network is reachable"
    actions.run_now()
    actions.open_settings()
    actions.quit()

    assert monitor.calls == ["run_now", "stop"]
    assert opened == [True]
    assert quit_calls == [True]


def test_tray_actions_include_traffic_summary_when_available():
    monitor = FakeMonitor()
    traffic = TrafficSnapshot(
        interface_name="Wi-Fi",
        upload_bytes_per_second=1024,
        download_bytes_per_second=2048,
        today_upload_bytes=3000,
        today_download_bytes=4000,
        month_upload_bytes=5000,
        month_download_bytes=6000,
        is_available=True,
    )
    actions = TrayActions(monitor, open_settings=lambda: None, quit_app=lambda: None, traffic_provider=lambda: traffic)

    assert actions.traffic_text() == "Wi-Fi: Up 1.0 KB/s, Down 2.0 KB/s"
    assert actions.usage_detail_text() == "Today 6.8 KB; Month 10.7 KB"


class FakeSettingsStore:
    def __init__(self):
        self.saved = []

    def save(self, settings):
        self.saved.append(settings)


class FakeCredentials:
    def __init__(self):
        self.saved = []

    def set_password(self, username, password):
        self.saved.append((username, password))


class FakeAutostart:
    def __init__(self):
        self.calls = []

    def enable(self):
        self.calls.append("enable")

    def disable(self):
        self.calls.append("disable")


def test_apply_tray_settings_saves_settings_password_and_enables_autostart():
    settings_store = FakeSettingsStore()
    credentials = FakeCredentials()
    autostart = FakeAutostart()

    apply_tray_settings(
        settings_store=settings_store,
        credentials=credentials,
        autostart=autostart,
        settings=UserSettings(username="test-user", autostart_enabled=True),
        password="secret",
    )

    assert settings_store.saved == [UserSettings(username="test-user", autostart_enabled=True)]
    assert credentials.saved == [("test-user", "secret")]
    assert autostart.calls == ["enable"]


def test_apply_tray_settings_disables_autostart_without_requiring_password():
    settings_store = FakeSettingsStore()
    autostart = FakeAutostart()

    apply_tray_settings(
        settings_store=settings_store,
        credentials=FakeCredentials(),
        autostart=autostart,
        settings=UserSettings(username="test-user", autostart_enabled=False),
        password="",
    )

    assert autostart.calls == ["disable"]


def test_tray_icon_path_points_to_packaged_png_asset():
    icon_path = tray_icon_path()

    assert icon_path.name == "tray_icon.png"
    assert icon_path.exists()
