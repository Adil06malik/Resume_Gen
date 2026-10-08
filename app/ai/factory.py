from typing import Optional
from app.config import settings
from app.ai.base import AIProvider
from app.ai.openai_provider import OpenAICompatibleProvider, OpenRouterProvider
from app.ai.anthropic_provider import AnthropicProvider
from app.ai.local_provider import LocalProvider


def get_ai_provider() -> AIProvider:
    provider_type = settings.AI_PROVIDER.lower()
    api_key = settings.AI_API_KEY
    base_url = settings.AI_BASE_URL
    model = settings.AI_MODEL

    if not api_key:
        raise ValueError("AI_API_KEY is not configured")

    if provider_type == "openrouter":
        return OpenRouterProvider(api_key=api_key, base_url=base_url, model=model)
    elif provider_type == "openai":
        return OpenAICompatibleProvider(api_key=api_key, base_url=base_url, model=model)
    elif provider_type == "anthropic":
        return AnthropicProvider(api_key=api_key, base_url=base_url, model=model)
    elif provider_type == "local":
        return LocalProvider(api_key=api_key, base_url=base_url, model=model)
    else:
        raise ValueError(f"Unknown AI provider: {provider_type}")