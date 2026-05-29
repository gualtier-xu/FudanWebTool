from fudan_web_tool.monitor import BackgroundMonitor


class FakeManager:
    def __init__(self):
        self.calls = 0

    def run_once(self):
        self.calls += 1
        return type("RecoveryResult", (), {"action": "already_online", "message": "ok"})()


def test_monitor_run_now_records_latest_status():
    manager = FakeManager()
    monitor = BackgroundMonitor(manager, interval=60)

    result = monitor.run_now()

    assert result.action == "already_online"
    assert manager.calls == 1
    assert monitor.status.last_action == "already_online"
    assert monitor.status.last_message == "ok"


def test_monitor_pause_and_resume_skip_automatic_cycle():
    manager = FakeManager()
    monitor = BackgroundMonitor(manager, interval=60)

    monitor.pause()
    monitor.run_cycle_if_active()
    assert manager.calls == 0
    assert monitor.status.is_paused is True

    monitor.resume()
    monitor.run_cycle_if_active()
    assert manager.calls == 1
    assert monitor.status.is_paused is False


def test_monitor_stop_marks_not_running():
    manager = FakeManager()
    monitor = BackgroundMonitor(manager, interval=60)

    monitor.start()
    monitor.stop()

    assert monitor.status.is_running is False


def test_monitor_stop_runs_close_callback_once():
    manager = FakeManager()
    closed = []
    monitor = BackgroundMonitor(manager, interval=60, close_callback=lambda: closed.append(True))

    monitor.stop()
    monitor.stop()

    assert closed == [True]
