# FudanWebTool

[中文文档](README-zh.md)

A lightweight tool for monitoring Fudan campus network connectivity and
automatically re-authenticating when disconnected.

It provides a foreground command-line monitor. The monitor checks real external
connectivity first, then uses the Fudan portal only when recovery is needed. If
the portal says authentication succeeded but the external network is still
unreachable, the tool logs out and signs in again with the campus network
channel.

## Features

- Periodic network health checks
- Campus gateway login request
- Safe configuration through environment variables
- Logs for reconnect attempts and failures
- False-online recovery by logging out before reconnecting

## Configuration

Copy `.env.example` to `.env` and fill in your local values before running
login commands. Keep real credentials in `.env` only.

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`; it is ignored by Git.

Available settings:

- `FUDAN_NET_USERNAME`: campus network username
- `FUDAN_NET_PASSWORD`: campus network password
- `FUDAN_NET_BASE_URL`: portal URL, defaults to `http://10.102.250.36`
- `FUDAN_NET_CHANNEL_NAME`: network channel, defaults to 校园网
- `FUDAN_NET_INTERVAL`: watch interval in seconds, defaults to `5`
- `FUDAN_NET_CHECK_TIMEOUT`: per-target connectivity timeout in seconds, defaults to `3`
- `FUDAN_NET_CHECK_URLS`: comma-separated external URLs for connectivity checks

## Documentation

Keep `README.md` and `README-zh.md` synchronized when changing user-facing
setup, configuration, or usage instructions.

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

If `conda activate` is not available in PowerShell, initialize Conda once and
restart the terminal:

```powershell
conda init powershell
```

The command-line entry point is installed into this Conda environment, so run
the tool after activating it:

```powershell
conda activate fudan-web-tool
fudan-web-tool status
```

Alternative plain Python virtual environment setup:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m pytest
```

## Usage

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
