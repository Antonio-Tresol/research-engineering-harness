"""Transport layer. Offline builds synthesize the wire payload the
service would return, deterministically from the request body."""

from __future__ import annotations

import zlib
from typing import Any

from .config import ClientConfig
from .exceptions import APIConnectionError


def post(config: ClientConfig, path: str, body: dict[str, Any]) -> dict[str, Any]:
    if not config.offline:
        raise APIConnectionError("online transport is not available in this build")
    prompt = str(body.get("prompt", ""))
    normalized = " ".join(prompt.split())[:48]
    return {
        "id": "cmpl-" + format(zlib.crc32(normalized.encode()), "010d"),
        "model": body.get("model", "chat-lite-3"),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": [
                        {"kind": "text", "text": "considered reply: "},
                        {"kind": "text", "text": normalized},
                    ],
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {"input_tokens": max(1, len(prompt) // 4), "output_tokens": 12},
    }
