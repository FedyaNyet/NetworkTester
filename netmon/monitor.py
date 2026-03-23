import subprocess
import time
import csv
import datetime
import re
import statistics
import argparse
from pathlib import Path
import ipaddress
import asyncio
import json
import threading
from aiohttp import web

# ----- CONFIG (defaults; can be overridden via CLI) -----
TEST_DURATION_SECONDS = float('inf')  # Run indefinitely (use Ctrl+C to stop)
PING_COUNT_PER_CYCLE = 2      # number of pings per cycle for jitter/loss
SLEEP_BETWEEN_CYCLES = 0      # seconds between cycles

# Optional packet sizing for Windows ping (payload size, default 32 bytes if None)
PACKET_SIZE_BYTES = None  # e.g., 200 or 1200; None uses system default
DF_DONT_FRAGMENT = False  # set True to add -f (Don't Fragment) for MTU testing
# Ping timeout per echo request (ms). Lower to avoid long stalls at high sampling rates.
PING_TIMEOUT_MS = 1000

# WebSocket server for live monitoring
WEBSOCKET_PORT = 8765
# -------------------------------------------------------

# Paths relative to project root
_ROOT = Path(__file__).parent.parent
WEB_DIR = _ROOT / 'web'
RUNS_DIR = _ROOT / 'runs'

# Global storage for WebSocket clients and event loop
websocket_clients = set()
websocket_loop = None
current_logfile = None


def run_ping(host, count):
    """Runs Windows ping and returns list of latency results in ms (None for loss)."""
    latencies = []
    if not host:
        return [None] * count
    base_cmd = ["ping", "-n", "1", "-w", str(PING_TIMEOUT_MS)]
    if DF_DONT_FRAGMENT:
        base_cmd.append("-f")
    if PACKET_SIZE_BYTES is not None:
        base_cmd += ["-l", str(PACKET_SIZE_BYTES)]
    for _ in range(count):
        cmd = list(base_cmd) + [host]
        try:
            output = subprocess.check_output(
                cmd,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            parsed = None
            for line in output.splitlines():
                match = re.search(r"time[=<](\d+)ms", line)
                if match:
                    parsed = int(match.group(1))
                    break
                if "Request timed out" in line or "unreachable" in line.lower():
                    parsed = None
            latencies.append(parsed)
        except subprocess.CalledProcessError:
            latencies.append(None)
    return latencies


def get_gateway():
    try:
        ps_cmd = (
            "(Get-NetRoute -DestinationPrefix '0.0.0.0/0'"
            " | Sort-Object -Property RouteMetric"
            " | Select-Object -First 1).NextHop"
        )
        output = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", ps_cmd], text=True
        ).strip()
        if re.match(r"\d+\.\d+\.\d+\.\d+", output):
            return output
    except Exception:
        pass

    try:
        output = subprocess.check_output("ipconfig", shell=True, text=True)
        lines = output.splitlines()
        for i, line in enumerate(lines):
            if "Default Gateway" in line:
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    return m.group(1)
                if i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if re.match(r"\d+\.\d+\.\d+\.\d+", nxt):
                        return nxt
    except Exception:
        pass
    return None


def get_first_hop(gateway_ip: str | None = None):
    """Return the first upstream hop beyond the gateway, preferring a public IP."""
    try:
        output = subprocess.check_output(["tracert", "-d", "-h", "6", "8.8.8.8"], text=True)
        hops: list[str] = []
        for line in output.splitlines():
            if re.match(r"^\s*\d+\s+", line):
                ips = re.findall(r"\d+\.\d+\.\d+\.\d+", line)
                if ips:
                    hops.append(ips[-1])
                else:
                    hops.append("")

        hops = [h for h in hops if h]
        if not hops:
            return None

        def is_private_or_special(ip: str) -> bool:
            try:
                addr = ipaddress.ip_address(ip)
            except ValueError:
                return True
            return (
                addr.is_private
                or addr.is_loopback
                or addr.is_link_local
                or addr.is_multicast
                or addr.is_reserved
                or addr.is_unspecified
            )

        for ip in hops:
            if gateway_ip and ip == gateway_ip:
                continue
            if not is_private_or_special(ip):
                return ip

        for ip in hops:
            if gateway_ip and ip == gateway_ip:
                continue
            return ip
    except Exception:
        pass
    return None


async def broadcast_to_clients(data):
    """Send data to all connected WebSocket clients."""
    if not websocket_clients:
        return
    disconnected = set()
    for ws in websocket_clients:
        try:
            await ws.send_json(data)
        except Exception:
            disconnected.add(ws)
    for ws in disconnected:
        websocket_clients.discard(ws)


async def websocket_handler(request):
    """Handle WebSocket connections from the widget."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    websocket_clients.add(ws)
    print(f"WebSocket client connected. Total clients: {len(websocket_clients)}")

    if current_logfile:
        try:
            def of(v):
                return None if v in ('', 'None') else float(v)
            rows = []
            with open(current_logfile, newline='', encoding='utf-8') as f:
                for row in csv.DictReader(f):
                    rows.append({
                        "timestamp":  row["Time"],
                        "gateway":    {"avg_ms": of(row["GW_avg_ms"]), "loss_pct": of(row["GW_loss_pct"]), "jitter_ms": of(row["GW_jitter_ms"])},
                        "first_hop":  {"avg_ms": of(row["FH_avg_ms"]), "loss_pct": of(row["FH_loss_pct"]), "jitter_ms": of(row["FH_jitter_ms"])},
                        "google_dns": {"avg_ms": of(row["GD_avg_ms"]), "loss_pct": of(row["GD_loss_pct"]), "jitter_ms": of(row["GD_jitter_ms"])},
                    })
            if rows:
                await ws.send_json({"type": "history", "rows": rows})
        except Exception:
            pass

    try:
        async for msg in ws:
            pass
    finally:
        websocket_clients.discard(ws)
        print(f"WebSocket client disconnected. Total clients: {len(websocket_clients)}")

    return ws


async def serve_widget(request):
    widget_path = WEB_DIR / 'widget.html'
    try:
        return web.Response(text=widget_path.read_text(encoding='utf-8'), content_type='text/html')
    except FileNotFoundError:
        return web.Response(text='Widget file not found', status=404)


async def serve_manifest(request):
    manifest_path = WEB_DIR / 'manifest.json'
    try:
        return web.Response(text=manifest_path.read_text(encoding='utf-8'), content_type='application/manifest+json')
    except FileNotFoundError:
        return web.Response(text='Manifest not found', status=404)


async def serve_main_report(request):
    report_path = WEB_DIR / 'report.html'
    if report_path.exists():
        return web.FileResponse(report_path)
    return web.Response(text='Report not found.', status=404)


async def start_websocket_server():
    app = web.Application()
    app.router.add_get("/ws", websocket_handler)
    app.router.add_get("/", serve_widget)
    app.router.add_get("/report", serve_main_report)
    app.router.add_get("/manifest.json", serve_manifest)
    app.router.add_static("/runs", str(RUNS_DIR), show_index=True)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "localhost", WEBSOCKET_PORT)
    await site.start()
    print(f"WebSocket server started on ws://localhost:{WEBSOCKET_PORT}/ws")
    print(f"Widget available at http://localhost:{WEBSOCKET_PORT}/")
    print(f"Report available at http://localhost:{WEBSOCKET_PORT}/report")


def run_websocket_server_thread():
    global websocket_loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    websocket_loop = loop
    loop.run_until_complete(start_websocket_server())
    loop.run_forever()


def generate_report(logfile: str):
    print(f"Test complete. CSV saved to: {logfile}")
    print("Open web/report.html and select the CSV from runs/ to view results.")


def parse_args():
    p = argparse.ArgumentParser(description="Network latency/loss tester (Windows)")
    p.add_argument("--duration", type=float, default=None, help="Total test duration in seconds")
    p.add_argument("--interval", type=float, default=None, help="Seconds to sleep between cycles")
    p.add_argument("--count", type=int, default=None, help="Ping count per cycle")
    p.add_argument("--packet-size", type=int, default=None, help="ICMP payload size in bytes (-l)")
    p.add_argument("--df", action="store_true", help="Set Don't Fragment flag (-f)")
    p.add_argument("--timeout-ms", type=int, default=None, help="Ping timeout per echo in ms (-w)")
    p.add_argument("--port", type=int, default=None, help="WebSocket server port (default 8765)")
    return p.parse_args()


def main():
    global TEST_DURATION_SECONDS, SLEEP_BETWEEN_CYCLES, PING_COUNT_PER_CYCLE
    global PACKET_SIZE_BYTES, DF_DONT_FRAGMENT, PING_TIMEOUT_MS, WEBSOCKET_PORT
    global current_logfile

    args = parse_args()
    if args.duration is not None:
        TEST_DURATION_SECONDS = args.duration
    if args.interval is not None:
        SLEEP_BETWEEN_CYCLES = args.interval
    if args.count is not None:
        PING_COUNT_PER_CYCLE = args.count
    if args.packet_size is not None:
        PACKET_SIZE_BYTES = args.packet_size
    if args.df:
        DF_DONT_FRAGMENT = True
    if args.timeout_ms is not None:
        PING_TIMEOUT_MS = args.timeout_ms
    if args.port is not None:
        WEBSOCKET_PORT = args.port

    gateway = get_gateway()
    first_hop = get_first_hop(gateway)
    google_dns = "8.8.8.8"

    print(f"Gateway: {gateway}")
    print(f"Comcast first hop: {first_hop}")
    print(f"Google DNS: {google_dns}")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    logfile = str(RUNS_DIR / f"{timestamp}.csv")
    current_logfile = logfile

    print(f"Saving data to: {logfile}")

    with open(logfile, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Time",
            "GW_avg_ms", "GW_loss_pct", "GW_jitter_ms",
            "FH_avg_ms", "FH_loss_pct", "FH_jitter_ms",
            "GD_avg_ms", "GD_loss_pct", "GD_jitter_ms"
        ])

    ws_thread = threading.Thread(target=run_websocket_server_thread, daemon=True)
    ws_thread.start()

    try:
        start_time = time.time()
        while time.time() - start_time < TEST_DURATION_SECONDS:
            now = datetime.datetime.now().strftime("%H:%M:%S")

            gw_pings = run_ping(gateway, PING_COUNT_PER_CYCLE)
            fh_pings = run_ping(first_hop, PING_COUNT_PER_CYCLE)
            gd_pings = run_ping(google_dns, PING_COUNT_PER_CYCLE)

            def stats(pings):
                valid = [p for p in pings if p is not None]
                if valid:
                    avg = sum(valid) / len(valid)
                    jit = statistics.pstdev(valid) if len(valid) > 1 else 0
                else:
                    avg = None
                    jit = None
                loss = (pings.count(None) / len(pings)) * 100
                return avg, loss, jit

            gw_avg, gw_loss, gw_jit = stats(gw_pings)
            fh_avg, fh_loss, fh_jit = stats(fh_pings)
            gd_avg, gd_loss, gd_jit = stats(gd_pings)

            with open(logfile, "a", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    now,
                    gw_avg, gw_loss, gw_jit,
                    fh_avg, fh_loss, fh_jit,
                    gd_avg, gd_loss, gd_jit
                ])

            print(f"{now} | GW: {gw_avg} ms ({gw_loss:.0f}% loss) | FH: {fh_avg} ms ({fh_loss:.0f}% loss) | GD: {gd_avg} ms ({gd_loss:.0f}% loss)")

            if websocket_clients and websocket_loop:
                data = {
                    "type": "data",
                    "timestamp": now,
                    "gateway": {"avg_ms": gw_avg, "loss_pct": gw_loss, "jitter_ms": gw_jit},
                    "first_hop": {"avg_ms": fh_avg, "loss_pct": fh_loss, "jitter_ms": fh_jit},
                    "google_dns": {"avg_ms": gd_avg, "loss_pct": gd_loss, "jitter_ms": gd_jit}
                }
                for ws in list(websocket_clients):
                    try:
                        asyncio.run_coroutine_threadsafe(
                            ws.send_json(data),
                            websocket_loop
                        )
                    except Exception:
                        pass

            time.sleep(SLEEP_BETWEEN_CYCLES)
    except KeyboardInterrupt:
        print("Interrupted by user. Generating report with collected data...")
    finally:
        generate_report(logfile)


if __name__ == "__main__":
    main()
