"""Response types.

A message's content is a list of blocks, not a string: providers return
mixed block kinds, and the SDK preserves them. The generated text of a
message is the concatenation of its text blocks.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .usage import Usage


@dataclass(frozen=True)
class ContentBlock:
    kind: str  # "text" is the only kind offline builds produce
    text: str


@dataclass(frozen=True)
class Message:
    role: str
    content: list[ContentBlock] = field(default_factory=list)


@dataclass(frozen=True)
class Choice:
    index: int
    message: Message
    finish_reason: str


@dataclass(frozen=True)
class Completion:
    id: str
    model: str
    choices: list[Choice]
    usage: Usage
