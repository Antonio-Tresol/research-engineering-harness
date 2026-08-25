"""Client configuration defaults."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_BASE_URL = "https://api.chat-sdk.invalid/v1"
DEFAULT_TIMEOUT_SECONDS = 60.0
DEFAULT_MAX_RETRIES = 2


@dataclass(frozen=True)
class ClientConfig:
    base_url: str = DEFAULT_BASE_URL
    timeout: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    offline: bool = True
