"""OpenAI provider."""

from app.llm.providers.custom import CustomProvider


class OpenAIProvider(CustomProvider):
    provider_name = "openai"

    def __init__(self, api_key: str, model: str, base_url: str | None = None) -> None:
        super().__init__(api_key, model, base_url or "https://api.openai.com/v1")

    async def list_models(self) -> list[str]:
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            resp.raise_for_status()
            return [m["id"] for m in resp.json().get("data", []) if "gpt" in m["id"]]
