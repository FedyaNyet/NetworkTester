import csv
import datetime
import argparse
from statistics import mean, median, stdev
from pathlib import Path

SPIKE_THRESHOLD_MS = 100   # FH latency above this = spike
SPIKE_GAP_SEC      = 10    # gap between samples that merges into same event

_ROOT = Path(__file__).parent.parent
RUNS_DIR = _ROOT / 'runs'


def opt_float(v):
    v = (v or '').strip()
    if v in ('', 'None'):
        return None
    try:
        return float(v)
    except ValueError:
        return None


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
    loss_cycles  = sum(1 for v in data['loss'] if v >= 100.0)
    loss_rate    = pct(loss_cycles, total_cycles)
    lat_values   = data['avg']
    jit_values   = [v for v in data['jitter'] if v is not None]

    longest_streak = current = bursts = 0
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
        q = quantiles(lat_values, [0.95, 0.99])
        print(f'  RTT ms  min={min(lat_values):.1f} med={median(lat_values):.1f} '
              f'avg={mean(lat_values):.1f} p95={q[0.95]:.1f} p99={q[0.99]:.1f} max={max(lat_values):.1f}')
    else:
        print('  RTT ms  (no successful samples)')
    if jit_values:
        q = quantiles(jit_values, [0.50, 0.95, 0.99])
        print(f'  Jitter  med={q[0.50]:.1f} p95={q[0.95]:.1f} p99={q[0.99]:.1f}')
    print(f'  Loss bursts={bursts} longest_streak={longest_streak} cycles')


def ts_seconds(t):
    if t is None:
        return None
    return t.hour * 3600 + t.minute * 60 + t.second


def main():
    p = argparse.ArgumentParser(description="Analyze network test CSV results")
    p.add_argument("csv", nargs='?', help="CSV file to analyze (default: most recent in runs/)")
    args = p.parse_args()

    if args.csv:
        csv_path = Path(args.csv)
        print(f"Analyzing: {csv_path.name}")
    else:
        csv_files = sorted(RUNS_DIR.glob('*.csv'), key=lambda x: x.stat().st_mtime, reverse=True)
        if csv_files:
            csv_path = csv_files[0]
            print(f"Analyzing most recent results: {csv_path.name}")
        else:
            print(f"No CSV files found in {RUNS_DIR}")
            raise SystemExit(1)

    if not csv_path.exists():
        print(f"No CSV found at {csv_path}")
        raise SystemExit(1)

    hosts = {
        'GW': {'avg': [], 'loss': [], 'jitter': []},
        'FH': {'avg': [], 'loss': [], 'jitter': []},
        'GD': {'avg': [], 'loss': [], 'jitter': []},
    }
    rows = []

    with csv_path.open(newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ts = datetime.datetime.strptime(row['Time'], '%H:%M:%S')
            except (ValueError, KeyError):
                ts = None

            gw = opt_float(row.get('GW_avg_ms'))
            fh = opt_float(row.get('FH_avg_ms'))
            gd = opt_float(row.get('GD_avg_ms'))
            rows.append((ts, gw, fh, gd))

            for key, prefix in [('GW', 'GW'), ('FH', 'FH'), ('GD', 'GD')]:
                avg  = opt_float(row.get(f'{prefix}_avg_ms'))
                loss = opt_float(row.get(f'{prefix}_loss_pct'))
                jit  = opt_float(row.get(f'{prefix}_jitter_ms'))
                if avg is not None: hosts[key]['avg'].append(avg)
                if jit is not None: hosts[key]['jitter'].append(jit)
                hosts[key]['loss'].append(100.0 if (loss is not None and loss >= 100.0) else 0.0)

    print()
    for key in ['GW', 'FH', 'GD']:
        summarize(key, hosts[key])

    # Spike event detection
    events = []
    current_event = None

    for ts, gw, fh, gd in rows:
        if fh is None:
            continue
        t = ts_seconds(ts)

        if fh >= SPIKE_THRESHOLD_MS:
            if current_event is None:
                current_event = {
                    'start': ts, 'start_sec': t,
                    'end': ts,   'end_sec': t,
                    'peak_fh': fh, 'peak_gw': gw or 0, 'peak_gd': gd or 0,
                    'samples': 1,
                    'gw_spiked': (gw or 0) >= SPIKE_THRESHOLD_MS,
                    'gd_spiked': (gd or 0) >= SPIKE_THRESHOLD_MS,
                }
            else:
                gap = (t - current_event['end_sec']) if (t and current_event['end_sec']) else 0
                if gap <= SPIKE_GAP_SEC:
                    current_event['end']      = ts
                    current_event['end_sec']  = t
                    current_event['peak_fh']  = max(current_event['peak_fh'], fh)
                    current_event['peak_gw']  = max(current_event['peak_gw'], gw or 0)
                    current_event['peak_gd']  = max(current_event['peak_gd'], gd or 0)
                    current_event['samples'] += 1
                    if (gw or 0) >= SPIKE_THRESHOLD_MS: current_event['gw_spiked'] = True
                    if (gd or 0) >= SPIKE_THRESHOLD_MS: current_event['gd_spiked'] = True
                else:
                    events.append(current_event)
                    current_event = {
                        'start': ts, 'start_sec': t,
                        'end': ts,   'end_sec': t,
                        'peak_fh': fh, 'peak_gw': gw or 0, 'peak_gd': gd or 0,
                        'samples': 1,
                        'gw_spiked': (gw or 0) >= SPIKE_THRESHOLD_MS,
                        'gd_spiked': (gd or 0) >= SPIKE_THRESHOLD_MS,
                    }
        else:
            if current_event is not None:
                events.append(current_event)
                current_event = None

    if current_event is not None:
        events.append(current_event)

    print(f'\n-- Spike Events (First Hop > {SPIKE_THRESHOLD_MS}ms) --------------------------------')
    if not events:
        print('  None found.')
    else:
        print(f'  {"#":>3}  {"Time":>8}  {"Peak FH":>8}  {"Peak GD":>8}  {"Dur(s)":>6}  {"GW?":>4}  {"GD?":>4}')
        print(f'  {"-"*3}  {"-"*8}  {"-"*8}  {"-"*8}  {"-"*6}  {"-"*4}  {"-"*4}')
        for i, e in enumerate(events, 1):
            start_str = e['start'].strftime('%H:%M:%S') if e['start'] else '?'
            dur = (e['end_sec'] - e['start_sec']) if (e['end_sec'] and e['start_sec']) else 0
            print(f'  {i:>3}  {start_str:>8}  {e["peak_fh"]:>7.0f}ms  {e["peak_gd"]:>7.0f}ms  '
                  f'{dur:>6.0f}s  {"yes":>4}' if e['gw_spiked'] else
                  f'  {i:>3}  {start_str:>8}  {e["peak_fh"]:>7.0f}ms  {e["peak_gd"]:>7.0f}ms  '
                  f'{dur:>6.0f}s  {"no":>4}',
                  end='')
            print(f'  {"yes":>4}' if e['gd_spiked'] else f'  {"no":>4}')

    if len(events) >= 2:
        intervals = []
        for a, b in zip(events, events[1:]):
            if a['start_sec'] is not None and b['start_sec'] is not None:
                diff = b['start_sec'] - a['start_sec']
                if diff > 0:
                    intervals.append(diff)

        if intervals:
            def fmt(s):
                m, sec = divmod(int(s), 60)
                return f'{m}m{sec:02d}s'

            print(f'\n-- Inter-Event Intervals ----------------------------------------------------')
            print(f'  Events:  {len(events)}')
            print(f'  Mean:    {fmt(mean(intervals))}  ({mean(intervals):.0f}s)')
            print(f'  Median:  {fmt(median(intervals))}  ({median(intervals):.0f}s)')
            if len(intervals) > 1:
                print(f'  Std dev: {stdev(intervals):.1f}s')
            print(f'  Min:     {fmt(min(intervals))}    Max: {fmt(max(intervals))}')
            print()
            print('  All intervals:')
            for i, (a, b, iv) in enumerate(zip(events, events[1:], intervals), 1):
                a_str = a['start'].strftime('%H:%M:%S') if a['start'] else '?'
                b_str = b['start'].strftime('%H:%M:%S') if b['start'] else '?'
                print(f'    {i:>3}.  {a_str} -> {b_str}  =  {fmt(iv)} ({iv:.0f}s)')


if __name__ == "__main__":
    main()
