import csv
import math
from statistics import mean, median
from pathlib import Path

CSV_PATH = Path(__file__).with_name('network_test.csv')

hosts = {
    'GW': {'avg': [], 'loss': [], 'jitter': []},
    'FH': {'avg': [], 'loss': [], 'jitter': []},
    'GD': {'avg': [], 'loss': [], 'jitter': []},
}

if not CSV_PATH.exists():
    print(f'No CSV found at {CSV_PATH}')
    raise SystemExit(1)

with CSV_PATH.open(newline='') as f:
    reader = csv.DictReader(f)
    for row in reader:
        # Each row has: Time,GW_avg_ms,GW_loss_pct,GW_jitter_ms,FH_avg_ms,FH_loss_pct,FH_jitter_ms,GD_avg_ms,GD_loss_pct,GD_jitter_ms
        def opt_float(v):
            v = (v or '').strip()
            if v in ('', 'None'):
                return None
            try:
                return float(v)
            except ValueError:
                return None
        for key, prefix in [('GW','GW'), ('FH','FH'), ('GD','GD')]:
            avg = opt_float(row.get(f'{prefix}_avg_ms'))
            loss = opt_float(row.get(f'{prefix}_loss_pct'))
            jit = opt_float(row.get(f'{prefix}_jitter_ms'))
            if avg is not None:
                hosts[key]['avg'].append(avg)
            if jit is not None:
                hosts[key]['jitter'].append(jit)
            # Treat None loss as 0 (only happens if earlier versions)
            hosts[key]['loss'].append(100.0 if (loss is not None and loss >= 100.0) else 0.0)


def pct(n, d):
    return 0.0 if d == 0 else (100.0 * n / d)

def quantiles(values, qs):
    if not values:
        return {q: None for q in qs}
    vs = sorted(values)
    res = {}
    for q in qs:
        idx = min(len(vs)-1, max(0, int(round(q * (len(vs)-1)))))
        res[q] = vs[idx]
    return res


def summarize(name, data):
    total_cycles = len(data['loss'])
    loss_cycles = sum(1 for v in data['loss'] if v >= 100.0)
    loss_rate = pct(loss_cycles, total_cycles)

    lat_values = data['avg']
    jit_values = [v for v in data['jitter'] if v is not None]

    lat_stats = {
        'count': len(lat_values),
        'min': min(lat_values) if lat_values else None,
        'median': median(lat_values) if lat_values else None,
        'avg': mean(lat_values) if lat_values else None,
        'p95': quantiles(lat_values, [0.95])[0.95] if lat_values else None,
        'p99': quantiles(lat_values, [0.99])[0.99] if lat_values else None,
        'max': max(lat_values) if lat_values else None,
    }

    # Longest consecutive loss streak
    longest_streak = 0
    current = 0
    bursts = 0
    for v in data['loss']:
        if v >= 100.0:
            current += 1
        else:
            if current > 0:
                bursts += 1
            longest_streak = max(longest_streak, current)
            current = 0
    if current > 0:
        bursts += 1
        longest_streak = max(longest_streak, current)

    print(f'[{name}] cycles={total_cycles} lost={loss_cycles} ({loss_rate:.2f}%)')
    if lat_values:
        print(f'  RTT ms  min={lat_stats["min"]:.1f} med={lat_stats["median"]:.1f} avg={lat_stats["avg"]:.1f} p95={lat_stats["p95"]:.1f} p99={lat_stats["p99"]:.1f} max={lat_stats["max"]:.1f}')
    else:
        print('  RTT ms  (no successful samples)')
    if jit_values:
        q = quantiles(jit_values, [0.50, 0.95, 0.99])
        print(f'  Jitter ms med={q[0.50]:.1f} p95={q[0.95]:.1f} p99={q[0.99]:.1f}')
    print(f'  Loss bursts={bursts} longest_streak={longest_streak} cycles')


for key in ['GW','FH','GD']:
    summarize(key, hosts[key])
