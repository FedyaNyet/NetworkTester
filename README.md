# NetworkTester

Measure latency, jitter, and packet loss to three targets (gateway, first hop, and Google DNS) on Windows. Logs results to a CSV and generates an interactive HTML report.

- Script: `network_test.py`
- Outputs: `network_test.csv`, `network_report.html`
- Platform: Windows (uses `ping`, `ipconfig`, `tracert`)

## Prerequisites
- Windows PowerShell
- [uv](https://github.com/astral-sh/uv) installed (manages Python and venv automatically)
- ICMP not blocked by firewall (so `ping` works)

## Quick start (recommended: uv-managed)
If this project already contains `pyproject.toml` and `uv.lock` (committed):

```powershell
# from the project folder
uv sync
uv run python .\network_test.py
```

If starting fresh (no `pyproject.toml` yet):

```powershell
# initialize a project and add dependencies
uv init
uv add plotly
uv sync

# run without activating the venv
uv run python .\network_test.py
```

Optional: activate the venv explicitly
```powershell
.\.venv\Scripts\Activate.ps1
python .\network_test.py
# when done
deactivate
```

## What the script does
- Discovers your default gateway and first hop automatically using `ipconfig` and `tracert`.
- Pings each target in cycles and writes per-cycle stats to CSV:
  - average latency (ms)
  - packet loss (%)
  - jitter (population std dev, ms)
- Generates `network_report.html` with Plotly showing latency over time and coloring points when loss occurs.

Default runtime is 1 hour. Adjust these constants at the top of `network_test.py`:
- `TEST_DURATION_SECONDS` (default 3600)
- `PING_COUNT_PER_CYCLE` (default 3)
- `SLEEP_BETWEEN_CYCLES` (seconds between cycles)

Stop early with Ctrl+C. Partial results are preserved in the CSV; the HTML report is generated at the end of a full run.

## Outputs
- `network_test.csv` — raw per-cycle metrics (time, avg, loss, jitter for each target)
- `network_report.html` — interactive chart; open it in your browser

## Dependency manifest options
- uv-managed (recommended): keep `pyproject.toml` and `uv.lock` under version control. Recreate the environment anywhere with:
  ```powershell
  uv sync
  ```
- Classic `requirements.txt` (optional):
  ```powershell
  uv pip freeze > requirements.txt
  # later
  uv pip install -r requirements.txt
  ```

Current third-party deps used by the script:
- `plotly`

## Docker note
A `Dockerfile` is included, but `network_test.py` calls Windows tools (`ping`, `ipconfig`, `tracert`). The provided base image (`python:3.12-slim`) is Linux, so the script will not run correctly inside that container as-is. To containerize you can either:
- Switch to Windows containers and use a Windows base image with Python, or
- Make the script cross-platform (use Linux equivalents like `ping -c`, `ip route`, `traceroute`).

## Troubleshooting
- Gateway/first hop show as `None`:
  - Ensure the machine has an active network connection.
  - Run `ipconfig` and `tracert -d 8.8.8.8` manually to confirm outputs.
  - As a workaround, hardcode targets near the top of `network_test.py`.
- `ModuleNotFoundError: plotly`: run `uv add plotly` (or `uv pip install plotly`).
- Ping blocked by policy: allow ICMP Echo in your firewall settings or run on a network that permits ping.

## Housekeeping
- Update dependencies:
  ```powershell
  uv lock --upgrade
  uv sync
  ```
- Reset the environment from scratch:
  ```powershell
  Remove-Item -Recurse -Force .\.venv
  uv sync
  ```
