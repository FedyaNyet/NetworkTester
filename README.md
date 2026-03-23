# NetworkTester

Monitors network latency, jitter, and packet loss to three targets (local gateway, ISP first hop, Google DNS 8.8.8.8) on Windows. Logs results to timestamped CSVs and serves a live widget for real-time monitoring.

- Platform: Windows (uses `ping`, `ipconfig`, `tracert`)
- All data saved to `runs/<timestamp>.csv`

## Prerequisites

- Windows 10/11
- [uv](https://github.com/astral-sh/uv) installed

## Quick start

```powershell
uv sync
uv run python network_test.py
```

Or double-click `scripts/launch_monitor.bat`.

## Commands

### Run the monitor

```powershell
uv run -m netmon.monitor
```

Starts logging to `runs/<timestamp>.csv` and serves the live widget at `http://localhost:8765/`.

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--duration` | 3600 | Total run time in seconds |
| `--interval` | 0 | Seconds to sleep between cycles |
| `--count` | 2 | Pings per cycle (affects jitter accuracy) |
| `--timeout-ms` | — | Ping timeout per echo in ms |
| `--packet-size` | — | ICMP payload size in bytes |
| `--df` | off | Set Don't Fragment flag |
| `--port` | 8765 | WebSocket server port |

Stop early with **Ctrl+C** — the CSV is preserved.

### Analyze results

```powershell
uv run -m netmon.analyze
```

Reads the most recent CSV in `runs/` and prints:
- Per-host summary (RTT min/med/avg/p95/p99/max, jitter, loss)
- Spike event table (events where first hop > 100ms, with timestamps and peak values)
- Inter-event interval analysis (mean, median, std dev — useful for identifying periodic patterns)

## Live widget

Open `http://localhost:8765/` in a browser while the monitor is running. Shows a live scrolling latency chart with the full current session history loaded on connect.

**RPT mode:** click the `RPT` button in the widget to load a historical CSV file instead of the live feed.

See [GAMEBAR_SETUP.md](GAMEBAR_SETUP.md) for pinning the widget as an always-on-top overlay.

## Viewing historical results

Open `web/report.html` in a browser and use the file picker to select any CSV from the `runs/` folder. Renders an interactive Plotly chart with statistics.

## Outputs

- `runs/<timestamp>.csv` — raw per-cycle metrics for each target
- `runs/.gitignore` — excludes CSVs from version control; the folder structure is tracked

## Tuning constants

At the top of `netmon/monitor.py`:

```python
TEST_DURATION_SECONDS = 3600   # default run length
PING_COUNT_PER_CYCLE  = 2      # pings per cycle (min 2 for jitter)
SLEEP_BETWEEN_CYCLES  = 0      # extra delay between cycles
```

## Troubleshooting

- **Gateway/first hop show as `None`:** run `ipconfig` and `tracert -d 8.8.8.8` manually to confirm your network is active. As a workaround, hardcode the targets near the top of `network_test.py`.
- **Widget shows "Connecting...":** make sure `network_test.py` is running and port 8765 is not blocked by your firewall.
- **`ModuleNotFoundError`:** run `uv sync` to install dependencies.
- **Ping blocked:** allow ICMP Echo in Windows Firewall or run on a network that permits ping.

## Dependency management

```powershell
# Recreate environment
uv sync

# Upgrade all deps
uv lock --upgrade && uv sync

# Reset from scratch
Remove-Item -Recurse -Force .\.venv && uv sync
```
