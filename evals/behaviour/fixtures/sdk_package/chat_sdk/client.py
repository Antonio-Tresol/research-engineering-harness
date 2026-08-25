"""Client entry points."""

from __future__ import annotations

from typing import Any

from . import transport
from .auth import resolve_api_key
from .config import ClientConfig
from .models import Choice, Completion, ContentBlock, Message, Usage


class Client:
    def __init__(self, api_key: "str | None" = None, config: "ClientConfig | None" = None) -> None:
        self.api_key = resolve_api_key(api_key)
        self.config = config or ClientConfig()

    def complete(self, prompt: str, *, model: str = "chat-lite-3") -> Completion:
        raw = transport.post(self.config, "/completions", {"prompt": prompt, "model": model})
        return _parse_completion(raw)


def complete(prompt: str, *, model: str = "chat-lite-3") -> Completion:
    """Module-level convenience mirroring Client.complete."""
    return Client().complete(prompt, model=model)


def _parse_completion(raw: dict[str, Any]) -> Completion:
    choices = [
        Choice(
            index=int(c["index"]),
            message=Message(
                role=c["message"]["role"],
                content=[
                    ContentBlock(kind=b["kind"], text=b["text"]) for b in c["message"]["content"]
                ],
            ),
            finish_reason=c["finish_reason"],
        )
        for c in raw["choices"]
    ]
    usage = Usage(**raw["usage"])
    return Completion(id=raw["id"], model=raw["model"], choices=choices, usage=usage)
