from __future__ import annotations

from app.ai.provider import AIProvider
from app.core.config import Settings, get_settings


def get_ai_provider(settings: Settings | None = None) -> AIProvider:
    settings = settings or get_settings()
    if settings.ai_provider == "anthropic" and settings.anthropic_api_key:
        from app.ai.anthropic_provider import AnthropicAIProvider

        return AnthropicAIProvider(settings.anthropic_api_key, settings.anthropic_model)
    from app.ai.fake_provider import FakeAIProvider

    return FakeAIProvider()


def estimate_cost_usd(input_tokens: int, output_tokens: int, settings: Settings | None = None) -> float:
    settings = settings or get_settings()
    cost = (input_tokens / 1_000_000) * settings.price_input_per_mtok + (
        output_tokens / 1_000_000
    ) * settings.price_output_per_mtok
    return round(cost, 6)
