#!/usr/bin/env python
'''benchmark.py — Automated comparison of InterCom video modules.

Runs each video module in localhost mode for a configurable duration,
captures the final statistics (bandwidth, MSE, PSNR), and produces
a CSV report + console summary.

Usage:
    python benchmark.py                          # 30s per test, all modules
    python benchmark.py --duration 60            # 60s per test
    python benchmark.py --modules minimal DEFLATE conditional  # subset
    python benchmark.py --output results.csv     # custom CSV path

Each test launches TWO instances of the module (sender + receiver on localhost)
so the full-duplex pipeline is exercised.

Requirements: same as InterCom (numpy, opencv, sounddevice, etc.)
'''

import subprocess
import sys
import os
import re
import time
import csv
import argparse
import signal

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# ── Module definitions ──────────────────────────────────────────────
# Each entry: (short_name, script, extra_args)
MODULES = [
    ("minimal_video",
     "minimal_video_TFG.py",
     []),

    ("DEFLATE_QSS2",
     "DEFLATE_video.py",
     ["--video_quantization_step_size", "2"]),

    ("DEFLATE_QSS4",
     "DEFLATE_video.py",
     ["--video_quantization_step_size", "4"]),

    ("conservative_QSS2",
     "DEFLATE_video_conservative.py",
     ["--video_quantization_step_size", "2"]),

    ("conditional_allblocks",
     "conditional_replenishment.py",
     ["--blocks_per_frame", "0",
      "--video_quantization_step_size", "2"]),

    ("conditional_all100",
     "conditional_replenishment.py",
     ["--blocks_per_frame", "100",
      "--video_quantization_step_size", "2"]),

    ("conditional_intra30",
     "conditional_replenishment.py",
     ["--blocks_per_frame", "100",
      "--intra_period", "30",
      "--video_quantization_step_size", "2"]),

    ("conditional_smart",
     "conditional_replenishment.py",
     ["--blocks_per_frame", "100",
      "--smart_refresh",
      "--video_quantization_step_size", "2"]),

    ("conditional_nack",
     "conditional_replenishment.py",
     ["--blocks_per_frame", "100",
      "--enable_nack",
      "--video_quantization_step_size", "2"]),

    ("conditional_full",
     "conditional_replenishment.py",
     ["--blocks_per_frame", "100",
      "--intra_period", "30",
      "--smart_refresh",
      "--enable_nack",
      "--video_quantization_step_size", "2"]),
]


def parse_output(text):
    '''Extract metrics from the program's final output.'''
    metrics = {
        'video_sent_kbps': 0.0,
        'video_recv_kbps': 0.0,
        'audio_sent_kbps': 0.0,
        'audio_recv_kbps': 0.0,
        'avg_mse': 0.0,
        'avg_psnr': 0.0,
        'total_time': 0.0,
        'frames_analyzed': 0,
        'avg_cpu': 0.0,
    }

    patterns = {
        'video_sent_kbps':  r'Video sent:\s+([\d.]+)\s+kbps',
        'video_recv_kbps':  r'Video received:\s+([\d.]+)\s+kbps',
        'audio_sent_kbps':  r'Audio sent:\s+([\d.]+)\s+kbps',
        'audio_recv_kbps':  r'Audio received:\s+([\d.]+)\s+kbps',
        'avg_mse':          r'Average MSE.*?:\s+([\d.]+)',
        'avg_psnr':         r'Average PSNR.*?:\s+([\d.]+)',
        'total_time':       r'Total time:\s+([\d.]+)',
        'frames_analyzed':  r'Frames analyzed:\s+(\d+)',
        'avg_cpu':          r'Average CPU usage:\s+([\d.]+)',
    }

    for key, pattern in patterns.items():
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            val = m.group(1)
            metrics[key] = int(val) if key == 'frames_analyzed' else float(val)

    return metrics


def run_test(name, script, extra_args, duration, port_base):
    '''Run a single test: launch the module in localhost mode for `duration` seconds.'''
    script_path = os.path.join(SCRIPT_DIR, script)
    if not os.path.exists(script_path):
        print(f"  SKIP: {script} not found")
        return None

    common_args = [
        sys.executable, script_path,
        "--destination_address", "localhost",
        "--show_stats",
        "--reading_time", str(duration),
        "--listening_video_port", str(port_base),
        "--destination_video_port", str(port_base),
    ]

    cmd = common_args + extra_args

    print(f"\n{'='*60}")
    print(f"  TEST: {name}")
    print(f"  CMD:  {' '.join(os.path.basename(c) for c in cmd)}")
    print(f"  Duration: {duration}s")
    print(f"{'='*60}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            cwd=SCRIPT_DIR,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
        )

        # The process self-terminates via --reading_time + SIGINT.
        # We just wait for it to finish, with a safety timeout.
        try:
            stdout, _ = proc.communicate(timeout=duration + 30)
        except subprocess.TimeoutExpired:
            print(f"  Timeout after {duration + 30}s, terminating...")
            if os.name == 'nt':
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.send_signal(signal.SIGINT)
            try:
                stdout, _ = proc.communicate(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, _ = proc.communicate()

        # Print last lines of output for visibility
        lines = stdout.strip().split('\n')
        print("\n  --- Output (last 20 lines) ---")
        for line in lines[-20:]:
            print(f"  {line}")

        metrics = parse_output(stdout)
        metrics['name'] = name
        metrics['script'] = script
        metrics['extra_args'] = ' '.join(extra_args)
        print(f"\n  RESULT: video={metrics['video_sent_kbps']:.1f} kbps, "
              f"MSE={metrics['avg_mse']:.2f}, PSNR={metrics['avg_psnr']:.2f} dB, "
              f"CPU={metrics['avg_cpu']:.1f}%")
        return metrics

    except Exception as e:
        print(f"  ERROR: {e}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark InterCom video modules",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("--duration", type=int, default=30,
        help="Seconds to run each test")
    parser.add_argument("--output", type=str, default="benchmark_results.csv",
        help="Output CSV file path")
    parser.add_argument("--modules", nargs="+", default=None,
        help="Run only these modules (by short name). "
             f"Available: {', '.join(m[0] for m in MODULES)}")
    parser.add_argument("--port", type=int, default=4445,
        help="Base video port for tests")
    args = parser.parse_args()

    # Filter modules if requested
    if args.modules:
        selected = [m for m in MODULES if m[0] in args.modules]
        if not selected:
            print(f"No matching modules. Available: {', '.join(m[0] for m in MODULES)}")
            return
    else:
        selected = MODULES

    print(f"\n{'#'*60}")
    print(f"  InterCom Video Benchmark")
    print(f"  Modules: {len(selected)}")
    print(f"  Duration per test: {args.duration}s")
    print(f"  Total estimated time: ~{len(selected) * (args.duration + 10)}s")
    print(f"{'#'*60}")

    results = []
    for name, script, extra_args in selected:
        metrics = run_test(name, script, extra_args, args.duration, args.port)
        if metrics:
            results.append(metrics)
        # Small pause between tests for socket cleanup
        time.sleep(3)

    if not results:
        print("\nNo results collected.")
        return

    # ── Write CSV ────────────────────────────────────────────────
    csv_path = os.path.join(SCRIPT_DIR, args.output)
    fieldnames = ['name', 'script', 'extra_args',
                  'video_sent_kbps', 'video_recv_kbps',
                  'audio_sent_kbps', 'audio_recv_kbps',
                  'avg_mse', 'avg_psnr', 'frames_analyzed', 'total_time', 'avg_cpu']
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow({k: r.get(k, '') for k in fieldnames})
    print(f"\nCSV saved: {csv_path}")

    # ── Console summary ─────────────────────────────────────────
    print(f"\n{'='*80}")
    print(f"  BENCHMARK SUMMARY")
    print(f"{'='*80}")
    print(f"{'Module':<25s} {'Video kbps':>12s} {'MSE':>10s} {'PSNR(dB)':>10s} {'Frames':>8s} {'CPU%':>7s}")
    print(f"{'-'*25} {'-'*12} {'-'*10} {'-'*10} {'-'*8} {'-'*7}")
    for r in results:
        print(f"{r['name']:<25s} "
              f"{r['video_sent_kbps']:>12.1f} "
              f"{r['avg_mse']:>10.2f} "
              f"{r['avg_psnr']:>10.2f} "
              f"{r['frames_analyzed']:>8d} "
              f"{r['avg_cpu']:>7.1f}")
    print(f"{'='*80}")

    # ── Key observations ────────────────────────────────────────
    if len(results) >= 2:
        baseline = results[0]
        best_bw = min(results, key=lambda r: r['video_sent_kbps'])
        best_quality = min(results, key=lambda r: r['avg_mse'])

        print(f"\n  Baseline ({baseline['name']}): {baseline['video_sent_kbps']:.1f} kbps")
        if best_bw['name'] != baseline['name']:
            saving = (1 - best_bw['video_sent_kbps'] / max(baseline['video_sent_kbps'], 0.01)) * 100
            print(f"  Lowest bandwidth: {best_bw['name']} ({best_bw['video_sent_kbps']:.1f} kbps, "
                  f"{saving:.0f}% reduction)")
        print(f"  Best quality: {best_quality['name']} (MSE={best_quality['avg_mse']:.2f})")


if __name__ == "__main__":
    main()
