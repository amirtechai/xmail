"""LLM provider factory — selects and instantiates the right provider."""

from app.core.crypto import get_crypto
from app.llm.base import BaseLLMProvider
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.custom import CustomProvider
from app.llm.providers.groq import GroqProvider
from app.llm.providers.openai import OpenAIProvider
from app.llm.providers.openrouter import OpenRouterProvider
from app.llm.providers.zai import ZaiProvider
from app.models.llm_config import LLMConfiguration, LLMProvider

_PROVIDER_MAP: dict[str, type[BaseLLMProvider]] = {
    LLMProvider.OPENROUTER.value: OpenRouterProvider,
    LLMProvider.OPENAI.value: OpenAIProvider,
    LLMProvider.ANTHROPIC.value: AnthropicProvider,
    LLMProvider.ZAI.value: ZaiProvider,
    LLMProvider.GROQ.value: GroqProvider,
    LLMProvider.CUSTOM.value: CustomProvider,
}


def build_provider(config: LLMConfiguration) -> BaseLLMProvider:
    crypto = get_crypto()
    api_key = crypto.decrypt(config.api_key_encrypted)
    provider_cls = _PROVIDER_MAP.get(config.provider)
    if not provider_cls:
        raise ValueError(f"Unknown LLM provider: {config.provider}")
    return provider_cls(api_key=api_key, model=config.model_name, base_url=config.base_url)
