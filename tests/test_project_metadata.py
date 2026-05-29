import struct
import tomllib
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_exposes_console_script():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert data["project"]["scripts"]["fudan-web-tool"] == "fudan_web_tool.cli:main"


def test_env_file_is_ignored_and_example_has_no_secrets():
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    env_example = (ROOT / ".env.example").read_text(encoding="utf-8")

    assert ".env" in gitignore
    assert "FUDAN_NET_PASSWORD=" in env_example
    assert "secret" not in env_example.lower()


def test_pyproject_declares_tray_and_packaging_dependencies():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert "PySide6>=6.7" in data["project"]["dependencies"]
    assert "keyring>=25.0" in data["project"]["dependencies"]
    assert "platformdirs>=4.0" in data["project"]["dependencies"]
    assert "psutil>=5.9" in data["project"]["dependencies"]
    assert "pyinstaller>=6.0" in data["project"]["optional-dependencies"]["build"]


def test_windows_packaging_files_exist():
    assert (ROOT / "fudan-web-tool-tray.spec").exists()
    assert (ROOT / "scripts" / "build-windows.ps1").exists()


def test_tray_icon_is_packaged():
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    spec = (ROOT / "fudan-web-tool-tray.spec").read_text(encoding="utf-8")

    assert (ROOT / "src" / "fudan_web_tool" / "assets" / "tray_icon.png").exists()
    assert data["tool"]["setuptools"]["package-data"]["fudan_web_tool"] == ["assets/tray_icon.png"]
    assert "collect_data_files(\"fudan_web_tool\")" in spec


def test_tray_icon_visible_content_fills_small_tray_size():
    width, height, pixels = _read_rgba_png(ROOT / "src" / "fudan_web_tool" / "assets" / "tray_icon.png")
    visible = [(x, y) for y, row in enumerate(pixels) for x, (_, _, _, alpha) in enumerate(row) if alpha > 16]
    min_x = min(x for x, _ in visible)
    max_x = max(x for x, _ in visible)
    min_y = min(y for _, y in visible)
    max_y = max(y for _, y in visible)

    assert (max_x - min_x + 1) / width >= 0.98
    assert (max_y - min_y + 1) / height >= 0.98


def test_windows_packaging_filters_conda_icu_dlls():
    spec = (ROOT / "fudan-web-tool-tray.spec").read_text(encoding="utf-8")

    assert "_without_conda_icu" in spec
    assert "icuuc.dll" in spec
    assert "icudt" in spec


def test_windows_packaging_replaces_base_openssl_dlls():
    spec = (ROOT / "fudan-web-tool-tray.spec").read_text(encoding="utf-8")

    assert "_with_current_env_openssl" in spec
    assert "libssl-3-x64.dll" in spec
    assert "libcrypto-3-x64.dll" in spec
    assert "sys.prefix" in spec


def _read_rgba_png(path: Path) -> tuple[int, int, list[list[tuple[int, int, int, int]]]]:
    data = path.read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    offset = 8
    chunks: list[tuple[bytes, bytes]] = []
    while offset < len(data):
        size = struct.unpack(">I", data[offset : offset + 4])[0]
        name = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + size]
        chunks.append((name, payload))
        offset += size + 12
        if name == b"IEND":
            break

    ihdr = dict(chunks)[b"IHDR"]
    width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", ihdr)
    assert bit_depth == 8
    assert color_type == 6
    raw = zlib.decompress(b"".join(payload for name, payload in chunks if name == b"IDAT"))
    stride = width * 4
    rows = []
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        row = bytearray(raw[cursor : cursor + stride])
        cursor += stride
        _unfilter(row, previous, filter_type, 4)
        rows.append([tuple(row[index : index + 4]) for index in range(0, stride, 4)])
        previous = row
    return width, height, rows


def _unfilter(row: bytearray, previous: bytearray, filter_type: int, bpp: int) -> None:
    for index in range(len(row)):
        left = row[index - bpp] if index >= bpp else 0
        up = previous[index]
        up_left = previous[index - bpp] if index >= bpp else 0
        if filter_type == 1:
            row[index] = (row[index] + left) & 0xFF
        elif filter_type == 2:
            row[index] = (row[index] + up) & 0xFF
        elif filter_type == 3:
            row[index] = (row[index] + ((left + up) // 2)) & 0xFF
        elif filter_type == 4:
            row[index] = (row[index] + _paeth(left, up, up_left)) & 0xFF
        else:
            assert filter_type == 0


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    distances = (abs(estimate - left), abs(estimate - up), abs(estimate - up_left))
    if distances[0] <= distances[1] and distances[0] <= distances[2]:
        return left
    if distances[1] <= distances[2]:
        return up
    return up_left
