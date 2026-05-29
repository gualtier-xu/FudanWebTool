# FudanWebTool

Tools for keeping Fudan campus network sessions online.

This project will provide a small automation script that monitors network
connectivity and re-authenticates when the campus gateway drops the session.

## Planned features

- Periodic network health checks
- Campus gateway login request
- Safe configuration through environment variables
- Logs for reconnect attempts and failures
- Optional background service setup

## Configuration

Copy `.env.example` to `.env` and fill in your local values when the login
implementation is added.

```powershell
Copy-Item .env.example .env
```

Do not commit `.env`; it is ignored by Git.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .[dev]
python -m pytest
```
