"""Streaming interface (offline builds yield one final event)."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any


def iter_events(payload: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield {"type": "message_stop", "payload": payload}
