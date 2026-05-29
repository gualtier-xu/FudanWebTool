from datetime import date

from fudan_web_tool.traffic import (
    InterfaceCounters,
    JsonTrafficStore,
    TrafficSampler,
    TrafficSnapshot,
    format_bytes,
    select_active_interface,
)


def test_traffic_sampler_calculates_speed_and_totals(tmp_path):
    store = JsonTrafficStore(tmp_path / "traffic.json")
    sampler = TrafficSampler(store=store, now=lambda: date(2026, 5, 29))

    sampler.sample({"Wi-Fi": InterfaceCounters(bytes_sent=1000, bytes_recv=2000)}, elapsed_seconds=1)
    snapshot = sampler.sample({"Wi-Fi": InterfaceCounters(bytes_sent=2500, bytes_recv=5000)}, elapsed_seconds=2)

    assert snapshot.interface_name == "Wi-Fi"
    assert snapshot.upload_bytes_per_second == 750
    assert snapshot.download_bytes_per_second == 1500
    assert snapshot.today_upload_bytes == 1500
    assert snapshot.today_download_bytes == 3000
    assert snapshot.month_upload_bytes == 1500
    assert snapshot.month_download_bytes == 3000


def test_traffic_sampler_ignores_negative_delta_after_reset(tmp_path):
    sampler = TrafficSampler(store=JsonTrafficStore(tmp_path / "traffic.json"), now=lambda: date(2026, 5, 29))

    sampler.sample({"Wi-Fi": InterfaceCounters(bytes_sent=5000, bytes_recv=5000)}, elapsed_seconds=1)
    snapshot = sampler.sample({"Wi-Fi": InterfaceCounters(bytes_sent=100, bytes_recv=200)}, elapsed_seconds=1)

    assert snapshot.upload_bytes_per_second == 0
    assert snapshot.download_bytes_per_second == 0
    assert snapshot.today_total_bytes == 0


def test_traffic_store_keeps_daily_and_monthly_totals_without_sensitive_words(tmp_path):
    path = tmp_path / "traffic.json"
    store = JsonTrafficStore(path)

    store.add_usage(date(2026, 5, 29), upload_bytes=100, download_bytes=200)
    store.add_usage(date(2026, 5, 30), upload_bytes=300, download_bytes=400)

    assert store.daily_total(date(2026, 5, 29)) == (100, 200)
    assert store.month_total(date(2026, 5, 1)) == (400, 600)
    assert "password" not in path.read_text(encoding="utf-8").lower()
    assert "token" not in path.read_text(encoding="utf-8").lower()


def test_select_active_interface_skips_loopback_and_virtual_names():
    counters = {
        "Loopback Pseudo-Interface 1": InterfaceCounters(bytes_sent=9000, bytes_recv=9000),
        "vEthernet (Default Switch)": InterfaceCounters(bytes_sent=9000, bytes_recv=9000),
        "Wi-Fi": InterfaceCounters(bytes_sent=1200, bytes_recv=2400),
    }

    assert select_active_interface(counters) == "Wi-Fi"


def test_format_bytes_uses_human_units():
    assert format_bytes(999) == "999 B"
    assert format_bytes(2048) == "2.0 KB"
    assert format_bytes(5 * 1024 * 1024) == "5.0 MB"


def test_empty_traffic_snapshot_reports_unavailable():
    snapshot = TrafficSnapshot.unavailable()

    assert snapshot.interface_name == ""
    assert snapshot.is_available is False
