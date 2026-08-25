"""Cursor pagination for list endpoints (unused by complete())."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Page:
    data: list[Any]
    has_more: bool
    next_cursor: "str | None"
