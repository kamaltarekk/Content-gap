"""Anthropic adapter. Keeps system instructions separate from untrusted source content, forces a
single JSON object, and does not set non-default sampling params for claude-sonnet-5 (spec §5.3,
§20.5). Never used in tests; the key lives only in backend env."""

from __future__ import annotations

import json
import re
from typing import Any

from app.ai.prompt_registry import SYSTEM_PREAMBLE, allowed_ids_block, load_prompt, wrap_source
from app.ai.provider import AIRequest, AIResponse, TokenCount
from app.core.text import detect_language

_INJECTION = re.compile(r"ignore (all|the|previous) instructions|reveal (your|the) (prompt|api key)", re.I)


class AnthropicAIProvider:
    def __init__(self, api_key: str, model: str) -> None:
        import anthropic

        self.name = "anthropic"
        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key)

    def count_tokens(self, request: AIRequest) -> TokenCount:
        text = str(request.payload.get("text", ""))
        return TokenCount(input_tokens=max(1, len(text) // 4 + 400), output_tokens=300)

    async def structured_generate(self, request: AIRequest, idempotency_key: str) -> AIResponse:
        payload = request.payload
        text = str(payload.get("text", ""))
        user = "\n\n".join(
            [
                load_prompt(request.task, request.prompt_version),
                allowed_ids_block(payload.get("evidence_ids", [])),
                f"content_piece_id: {payload.get('content_piece_id')}",
                f"language: {payload.get('language') or detect_language(text)}",
                wrap_source(text),
                "Return ONLY the JSON object.",
            ]
        )
        res = self._client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=SYSTEM_PREAMBLE,
            messages=[{"role": "user", "content": user}],
        )
        body = "".join(getattr(b, "text", "") for b in res.content)
        raw = _extract_json(body)
        suspicious = [m.group(0) for m in [_INJECTION.search(text)] if m]
        return AIResponse(
            raw=raw,
            usage=TokenCount(res.usage.input_tokens, res.usage.output_tokens),
            suspicious_instructions=suspicious,
        )


def _extract_json(text: str) -> dict[str, Any]:
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    candidate = fenced.group(1) if fenced else text
    start, end = candidate.find("{"), candidate.rfind("}")
    if start < 0 or end < 0:
        raise ValueError("model response contained no JSON object")
    return json.loads(candidate[start : end + 1])
