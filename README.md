# FudanWebTool

[中文文档](README-zh.md)

A lightweight Windows tray tool for monitoring Fudan campus network connectivity
and automatically re-authenticating when disconnected.

The tray app runs in the background without a persistent console window. It
checks real external connectivity first, then uses the Fudan portal only when
recovery is needed. If the portal says authentication succeeded but the external
network is still unreachable, the tool logs out and signs in again with the
campus network channel.

## Features

- Windows system tray icon with status, check-now, pause/resume, settings, and quit actions
- Periodic network health checks
- Campus gateway login request
- User settings stored in `%APPDATA%\FudanWebTool\config.json`
- Password stored through Windows Credential Manager via `keyring`
- Logs for reconnect attempts and failures
- False-online recovery by logging out before reconnecting

## Configuration

The tray settings window is the preferred configuration path. It stores
non-sensitive settings in `%APPDATA%\FudanWebTool\config.json` and stores the
password in Windows Credential Manager.

`.env` remains supported for command-line use and migration. Copy
`.env.example` to `.env` only if you want to use environment-based setup:

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`; it is ignored by Git.

Available settings:

- `FUDAN_NET_USERNAME`: campus network username
- `FUDAN_NET_PASSWORD`: campus network password for `.env` mode
- `FUDAN_NET_BASE_URL`: portal URL, defaults to `http://10.102.250.36`
- `FUDAN_NET_CHANNEL_NAME`: network channel, defaults to campus network
- `FUDAN_NET_INTERVAL`: watch interval in seconds, defaults to `5`
- `FUDAN_NET_CHECK_TIMEOUT`: per-target connectivity timeout in seconds, defaults to `3`
- `FUDAN_NET_CHECK_URLS`: comma-separated external URLs for connectivity checks

Tray settings take priority over `.env`; `.env` takes priority over built-in
defaults.

## Development

Use an Anaconda/Miniconda environment for local development and testing:

```powershell
conda env create -f environment.yml
conda activate fudan-web-tool
python -m pytest
```

If the environment already exists, update it after dependency changes:

```powershell
conda env update -f environment.yml --prune
conda activate fudan-web-tool
```

Alternative plain Python virtual environment setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev,build]
python -m pytest
```

## Usage

Run as a Windows tray app:

```powershell
fudan-web-tool tray
```

This starts a detached background tray process and then returns control to the
terminal. Closing the terminal does not close the tray app. Use the tray menu's
Quit action to stop it.

For troubleshooting only, run the tray loop in the current terminal:

```powershell
fudan-web-tool tray --foreground
```

Check current status without logging in:

```powershell
fudan-web-tool status
```

Run one recovery attempt:

```powershell
fudan-web-tool once
```

Keep monitoring in the foreground:

```powershell
fudan-web-tool watch
```

## Build EXE

After installing the build dependencies, create the tray executable:

```powershell
.\scripts\build-windows.ps1
```

The PyInstaller spec sets `console=False`, so the packaged app starts as a
background tray program instead of a persistent console window.

## Documentation

Keep `README.md` and `README-zh.md` synchronized when changing user-facing
setup, configuration, or usage instructions.
