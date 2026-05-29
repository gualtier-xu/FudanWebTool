# PyInstaller spec for the Windows tray executable.

from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

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
