"""Credential resolution (offline builds never send it anywhere)."""

from __future__ import annotations

import os


def resolve_api_key(explicit: "str | None" = None) -> str:
    if explicit:
        return explicit
    return os.environ.get("CHAT_SDK_API_KEY", "offline-key")
