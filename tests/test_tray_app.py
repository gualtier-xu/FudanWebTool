from fudan_web_tool.tray_app import TrayActions


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
