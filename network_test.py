import subprocess
import time
import csv
import datetime
import re
import statistics
import argparse
import plotly.graph_objects as go

# ----- CONFIG (defaults; can be overridden via CLI) -----
TEST_DURATION_SECONDS = 3600  # 1 hour
PING_COUNT_PER_CYCLE = 3      # number of pings per cycle for jitter/loss
SLEEP_BETWEEN_CYCLES = 1      # seconds between cycles

# Optional packet sizing for Windows ping (payload size, default 32 bytes if None)
PACKET_SIZE_BYTES = None  # e.g., 200 or 1200; None uses system default
DF_DONT_FRAGMENT = False  # set True to add -f (Don't Fragment) for MTU testing
# Ping timeout per echo request (ms). Lower to avoid long stalls at high sampling rates.
PING_TIMEOUT_MS = 1000
# -------------------------------------------------------

def run_ping(host, count):
    """Runs Windows ping and returns list of latency results in ms (None for loss)."""
    latencies = []
    # If host is missing/None, treat as total loss for this cycle
    if not host:
        return [None] * count
    # To increase resolution, send single-echo requests in a loop with a short timeout
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
            # Treat as lost packet for this echo
            latencies.append(None)
    return latencies

def get_gateway():
    # Try PowerShell: get best default route's next hop (IPv4)
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

    # Fallback: parse ipconfig; handle cases where the IP is on the next line
    try:
        output = subprocess.check_output("ipconfig", shell=True, text=True)
        lines = output.splitlines()
        for i, line in enumerate(lines):
            if "Default Gateway" in line:
                # Prefer IPv4-looking tokens on the same line
                m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
                if m:
                    return m.group(1)
                # Or on the next line (common formatting)
                if i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if re.match(r"\d+\.\d+\.\d+\.\d+", nxt):
                        return nxt
    except Exception:
        pass
    return None

def get_first_hop():
    try:
        output = subprocess.check_output(["tracert", "-d", "8.8.8.8"], text=True)
        for line in output.splitlines():
            if re.search(r"\*", line):
                # skip timeout-only hop lines
                continue
            m = re.search(r"(\d+\.\d+\.\d+\.\d+)", line)
            if m:
                return m.group(1)
    except Exception:
        pass
    return None

def generate_report(logfile: str):
    # ----- Generate HTML Graph -----
    times = []
    gw_avg, gw_loss = [], []
    fh_avg, fh_loss = [], []
    gd_avg, gd_loss = [], []

    with open(logfile, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            times.append(row["Time"])
            # Helper parsers: CSV may contain empty strings for None
            def opt_float(val):
                return None if val in ("", "None", None) else float(val)
            def req_float(val, default=0.0):
                try:
                    return float(val)
                except (TypeError, ValueError):
                    return default

            gw_avg.append(opt_float(row.get("GW_avg_ms")))
            fh_avg.append(opt_float(row.get("FH_avg_ms")))
            gd_avg.append(opt_float(row.get("GD_avg_ms")))
            gw_loss.append(req_float(row.get("GW_loss_pct")))
            fh_loss.append(req_float(row.get("FH_loss_pct")))
            gd_loss.append(req_float(row.get("GD_loss_pct")))

    if not times:
        print("No data collected; skipping report generation.")
        return

    def loss_colors(loss_list, normal_color, loss_color):
        """Returns list of colors for each point depending on packet loss."""
        return [loss_color if loss > 0 else normal_color for loss in loss_list]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=times, y=gw_avg, mode="markers+lines", name="Gateway",
        marker=dict(color=loss_colors(gw_loss, "blue", "red"), size=6),
        text=[f"Loss: {loss:.0f}%<br>Latency: {lat}" for loss, lat in zip(gw_loss, gw_avg)]
    ))
    fig.add_trace(go.Scatter(
        x=times, y=fh_avg, mode="markers+lines", name="First Hop",
        marker=dict(color=loss_colors(fh_loss, "green", "red"), size=6),
        text=[f"Loss: {loss:.0f}%<br>Latency: {lat}" for loss, lat in zip(fh_loss, fh_avg)]
    ))
    fig.add_trace(go.Scatter(
        x=times, y=gd_avg, mode="markers+lines", name="Google DNS",
        marker=dict(color=loss_colors(gd_loss, "orange", "red"), size=6),
        text=[f"Loss: {loss:.0f}%<br>Latency: {lat}" for loss, lat in zip(gd_loss, gd_avg)]
    ))
    fig.update_layout(
        title="Network Latency & Packet Loss Over Time",
        xaxis_title="Time",
        yaxis_title="Latency (ms)",
        hovermode="x unified"
    )
    fig.write_html("network_report.html")
    print("✅ Test complete. Open 'network_report.html' for results.")


def parse_args():
    p = argparse.ArgumentParser(description="Network latency/loss tester (Windows)")
    p.add_argument("--duration", type=float, default=None, help="Total test duration in seconds")
    p.add_argument("--interval", type=float, default=None, help="Seconds to sleep between cycles")
    p.add_argument("--count", type=int, default=None, help="Ping count per cycle")
    p.add_argument("--packet-size", type=int, default=None, help="ICMP payload size in bytes (-l)")
    p.add_argument("--df", action="store_true", help="Set Don't Fragment flag (-f)")
    p.add_argument("--timeout-ms", type=int, default=None, help="Ping timeout per echo in ms (-w)")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    # Override defaults if provided
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

    gateway = get_gateway()
    first_hop = get_first_hop()
    google_dns = "8.8.8.8"

    print(f"Gateway: {gateway}")
    print(f"Comcast first hop: {first_hop}")
    print(f"Google DNS: {google_dns}")

    logfile = "network_test.csv"

    # Write header
    with open(logfile, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "Time",
            "GW_avg_ms", "GW_loss_pct", "GW_jitter_ms",
            "FH_avg_ms", "FH_loss_pct", "FH_jitter_ms",
            "GD_avg_ms", "GD_loss_pct", "GD_jitter_ms"
        ])

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
            time.sleep(SLEEP_BETWEEN_CYCLES)
    except KeyboardInterrupt:
        print("Interrupted by user. Generating report with collected data...")
    finally:
        generate_report(logfile)
