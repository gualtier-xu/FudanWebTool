# PyInstaller spec for the Windows tray executable.

import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None


def _without_conda_icu(entries):
    """Let QtCore use Windows ICU instead of bundling conda/base ICU DLLs."""
    blocked_names = {"icuuc.dll"}
    return [
        entry
        for entry in entries
        if entry[0].lower() not in blocked_names and not entry[0].lower().startswith("icudt")
    ]


def _with_current_env_openssl(entries):
    """Use OpenSSL DLLs from the build environment, not conda/base."""
    openssl_names = {"libssl-3-x64.dll", "libcrypto-3-x64.dll"}
    env_bin = Path(sys.prefix) / "Library" / "bin"
    result = [entry for entry in entries if entry[0].lower() not in openssl_names]
    for name in sorted(openssl_names):
        dll_path = env_bin / name
        if dll_path.exists():
            result.append((name, str(dll_path), "BINARY"))
    return result

a = Analysis(
    ["src/fudan_web_tool/tray_main.py"],
    pathex=["src"],
    binaries=[],
    datas=collect_data_files("fudan_web_tool"),
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
a.binaries = _without_conda_icu(a.binaries)
a.binaries = _with_current_env_openssl(a.binaries)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="FudanWebTool",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
