"""Retry backoff schedule (unused offline, kept for API parity)."""

from __future__ import annotations


def schedule(max_retries: int, base: float = 0.5, cap: float = 8.0) -> list[float]:
    delays = []
    delay = base
    for _ in range(max_retries):
        delays.append(min(delay, cap))
        delay *= 2
    return delays
