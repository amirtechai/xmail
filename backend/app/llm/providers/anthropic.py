"""Anthropic provider via Messages API."""

import httpx

from app.llm.base import BaseLLMProvider, LLMMessage, LLMResponse

_API_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"

_AVAILABLE_MODELS = [
    "claude-opus-4-7",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
]


class AnthropicProvider(BaseLLMProvider):
    provider_name = "anthropic"

    async def complete(
        self,
        messages: list[LLMMessage],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        system_msgs = [m.content for m in messages if m.role == "system"]
        chat_msgs = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

        payload: dict = {
            "model": self.model,
            "messages": chat_msgs,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_msgs:
            payload["system"] = "\n\n".join(system_msgs)

        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                _API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": _API_VERSION,
                    "content-type": "application/json",
                },
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            return LLMResponse(
                content=data["content"][0]["text"],
                model=data.get("model", self.model),
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                finish_reason=data.get("stop_reason", "end_turn"),
                raw=data,
            )

    async def list_models(self) -> list[str]:
        return _AVAILABLE_MODELS
