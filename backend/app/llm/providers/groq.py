"""Groq provider — OpenAI-compatible, ultra-fast inference."""

from app.llm.providers.custom import CustomProvider


class GroqProvider(CustomProvider):
    provider_name = "groq"

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        super().__init__(api_key, model, base_url or "https://api.groq.com/openai/v1")
