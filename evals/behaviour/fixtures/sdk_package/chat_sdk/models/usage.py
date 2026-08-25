"""Token accounting attached to every completion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
