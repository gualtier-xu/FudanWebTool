Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

python -m PyInstaller fudan-web-tool-tray.spec --clean --noconfirm
