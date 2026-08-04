"""AI provider abstraction (spec §20.4). The domain layer never imports the Anthropic SDK."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class TokenCount:
    input_tokens: int
    output_tokens: int


@dataclass
class AIRequest:
    task: str
    payload: dict[str, Any]
    system: str = ""
    prompt_version: str = "v1"


@dataclass
class AIResponse:
    raw: dict[str, Any]
    usage: TokenCount
    # Instruction-like spans found in source content — logged, NEVER obeyed (spec §6.11).
    suspicious_instructions: list[str] = field(default_factory=list)


class AIProvider(Protocol):
    name: str
    model: str

    def count_tokens(self, request: AIRequest) -> TokenCount: ...
    async def structured_generate(self, request: AIRequest, idempotency_key: str) -> AIResponse: ...
