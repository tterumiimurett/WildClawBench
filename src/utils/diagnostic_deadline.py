"""Opt-in diagnostic timing; never used by standard benchmark runs."""
import json
import subprocess
import time
from pathlib import Path


def excluded_wait(log_path: Path, start: float, now: float) -> float:
    """Union of actual/pending proxy sleep intervals inside this execution."""
    intervals = []
    pending = {}
    try:
        lines = log_path.read_text().splitlines()
    except FileNotFoundError:
        return 0.0
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue  # the proxy may be appending the last line
        if event.get('event') == 'diagnostic_wait_start':
            pending[event['id']] = event['monotonic']
        elif event.get('event') == 'diagnostic_wait_end':
            began = pending.pop(event['id'], None)
            if began is not None:
                intervals.append((began, event['monotonic']))
    intervals.extend((began, now) for began in pending.values())
    total, end = 0.0, start
    for a, b in sorted(intervals):
        a, b = max(a, start, end), min(b, now)
        if b > a:
            total += b-a
            end = b
    return total


def wait_with_proxy_excluded(proc, budget: float, log_path: Path, metrics_path: Path):
    start = time.monotonic()
    try:
        while True:
            now = time.monotonic()
            remaining = budget - (now-start-excluded_wait(log_path, start, now))
            # Bound this diagnostic even if a proxy dies mid-sleep.
            wall_remaining = 3600 - (now-start)
            if remaining <= 0 or wall_remaining <= 0:
                raise subprocess.TimeoutExpired(proc.args, budget)
            try:
                return proc.wait(timeout=min(1.0, remaining, wall_remaining))
            except subprocess.TimeoutExpired:
                pass
    finally:
        now = time.monotonic()
        excluded = excluded_wait(log_path, start, now)
        metrics_path.write_text(json.dumps({'wall_seconds': now-start,
            'proxy_wait_seconds': excluded, 'charged_seconds': now-start-excluded,
            'budget_seconds': budget, 'diagnostic_only': True}, indent=2)+'\n')
