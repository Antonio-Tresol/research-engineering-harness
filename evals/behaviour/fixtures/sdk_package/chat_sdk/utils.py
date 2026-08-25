"""Small helpers shared across the package."""

from __future__ import annotations


def coalesce(*values):
    for value in values:
        if value is not None:
            return value
    return None
