import subprocess
import time
import csv
import datetime
import re
import statistics
import plotly.graph_objects as go

# ----- CONFIG -----
TEST_DURATION_SECONDS = 3600  # 1 hour
PING_COUNT_PER_CYCLE = 3      # number of pings per cycle for jitter/loss
SLEEP_BETWEEN_CYCLES = 1      # seconds between cycles
# ------------------

def run_ping(host, count):
    """Runs Windows ping and returns list of latency results in ms (None for loss)."""
    latencies = []
    try:
        output = subprocess.check_output(
            ["ping", "-n", str(count), host],
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        for line in output.splitlines():
            match = re.search(r"time[=<](\d+)ms", line)
            if match:
                latencies.append(int(match.group(1)))
            elif "Request timed out" in line or "unreachable" in line.lower():
                latencies.append(None)
    except subprocess.CalledProcessError:
        latencies = [None] * count
    return latencies

def get_gateway():
    output = subprocess.check_output("ipconfig", shell=True, text=True)
    for line in output.splitlines():
        if "Default Gateway" in line:
            parts = line.split(":")
            if len(parts) > 1:
                ip = parts[1].strip()
                if ip:
                    return ip
    return None

def get_first_hop():
    try:
        output = subprocess.check_output(["tracert", "-d", "8.8.8.8"], text=True)
        lines = output.splitlines()
        if len(lines) >= 3:
            first_hop_line = lines[3]
            parts = first_hop_line.split()
            for p in parts:
                if re.match(r"\d+\.\d+\.\d+\.\d+", p):
                    return p
    except:
        pass
    return None

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

# ----- Generate HTML Graph -----
times = []
gw_avg, gw_loss = [], []
fh_avg, fh_loss = [], []
gd_avg, gd_loss = [], []

with open(logfile, newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        times.append(row["Time"])
        gw_avg.append(None if row["GW_avg_ms"] == "None" else float(row["GW_avg_ms"]))
        fh_avg.append(None if row["FH_avg_ms"] == "None" else float(row["FH_avg_ms"]))
        gd_avg.append(None if row["GD_avg_ms"] == "None" else float(row["GD_avg_ms"]))
        gw_loss.append(float(row["GW_loss_pct"]))
        fh_loss.append(float(row["FH_loss_pct"]))
        gd_loss.append(float(row["GD_loss_pct"]))

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
