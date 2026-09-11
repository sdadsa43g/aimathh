"""Lightweight in-process metrics (Prometheus-compatible exposition later)."""

from __future__ import annotations

import time
from collections import Counter


class Metrics:
    def __init__(self) -> None:
        self.started = time.time()
        self.counters: Counter[str] = Counter()
        self.timings: dict[str, list[float]] = {}

    def inc(self, name: str, n: int = 1) -> None:
        self.counters[name] += n

    def observe(self, name: str, seconds: float) -> None:
        self.timings.setdefault(name, []).append(seconds)

    def snapshot(self) -> dict:
        out: dict = {"uptime_s": time.time() - self.started, "counters": dict(self.counters)}
        for k, v in self.timings.items():
            if v:
                out.setdefault("timings", {})[k] = {"n": len(v), "mean_s": sum(v) / len(v), "max_s": max(v)}
        return out


_metrics = Metrics()


def get_metrics() -> Metrics:
    return _metrics
