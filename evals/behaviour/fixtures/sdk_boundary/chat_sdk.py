"""Offline stand-in for a chat-completions SDK: deterministic, no network.

complete() returns a Completion; choices[0].message holds the generated text.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    role: str
    text: str


@dataclass(frozen=True)
class Choice:
    index: int
    message: Message
    finish_reason: str


@dataclass(frozen=True)
class Completion:
    model: str
    choices: list[Choice]


def complete(prompt: str, *, model: str = "stub-chat-1") -> Completion:
    reply = "considered reply: " + " ".join(prompt.split())[:48]
    message = Message(role="assistant", text=reply)
    return Completion(model=model, choices=[Choice(index=0, message=message, finish_reason="stop")])
