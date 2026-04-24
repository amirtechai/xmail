"""Z.ai (01.AI) provider — OpenAI-compatible."""

from app.llm.providers.custom import CustomProvider


class ZaiProvider(CustomProvider):
    provider_name = "zai"

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        super().__init__(api_key, model, base_url or "https://api.01.ai/v1")
