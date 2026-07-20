"""Deterministic flaky mock API for the observability probe.

Behaves like a slow, unreliable model endpoint. Failures are a pure function of
(item_id, attempt), so every run of the eval sees identical behaviour:

- items where md5(item_id) % 10 == 3 raise MockTimeout on their FIRST attempt
  and succeed on any later attempt (transient — a retry fixes them);
- items where md5(item_id) % 50 == 7 raise MockAPIError on EVERY attempt
  (permanent — retrying is wasted budget, the item must be recorded as failed);
- everything else succeeds immediately.

Use it as: `from mock_api import call_model` then `call_model(item_id, text)`.
"""

from __future__ import annotations

import hashlib
import time

_attempts: dict[str, int] = {}


class MockTimeout(Exception):
    """Transient failure; succeeds if retried."""


class MockAPIError(Exception):
    """Permanent failure; never succeeds."""


def _bucket(item_id: str, mod: int) -> int:
    return int(hashlib.md5(item_id.encode(), usedforsecurity=False).hexdigest(), 16) % mod


def call_model(item_id: str, text: str) -> dict[str, object]:
    """Score one item. ~50ms latency; raises per the schedule above."""
    time.sleep(0.05)
    _attempts[item_id] = _attempts.get(item_id, 0) + 1
    if _bucket(item_id, 50) == 7:
        raise MockAPIError(f"upstream rejected item {item_id!r} (permanent)")
    if _bucket(item_id, 10) == 3 and _attempts[item_id] == 1:
        raise MockTimeout(f"timeout scoring item {item_id!r} (transient)")
    score = _bucket(item_id + text, 1000) / 1000.0
    return {"item_id": item_id, "score": round(score, 3), "model": "mock-1"}
