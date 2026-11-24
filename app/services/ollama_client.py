import json
import logging
from collections.abc import AsyncIterator, Iterable
from typing import Any

import httpx

from app.core.config import Settings
from app.schemas.chat import ChatMessage
from app.utils.exceptions import (
    OllamaModelError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def status(self) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.settings.ollama_timeout) as client:
                response = await client.get(f"{self.settings.ollama_base_url}/api/tags")
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("Ollama status request timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaUnavailableError(
                f"Ollama is unavailable at {self.settings.ollama_base_url}"
            ) from exc

        models = [model.get("name", "") for model in data.get("models", [])]
        return {
            "connected": True,
            "models": models,
            "model_available": self.settings.ollama_model in models,
        }

    def _payload(
        self,
        messages: Iterable[ChatMessage],
        temperature: float,
        max_tokens: int | None,
        stream: bool,
    ) -> dict[str, Any]:
        options: dict[str, Any] = {"temperature": temperature}
        if max_tokens is not None:
            options["num_predict"] = max_tokens
        return {
            "model": self.settings.ollama_model,
            "messages": [
                {"role": message.role, "content": message.content}
                for message in messages
            ],
            "stream": stream,
            "think": False,
            "options": options,
        }

    async def chat(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int | None,
    ) -> str:
        payload = self._payload(messages, temperature, max_tokens, stream=False)
        try:
            async with httpx.AsyncClient(timeout=self.settings.ollama_timeout) as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url}/api/chat", json=payload
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("Ollama chat request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaModelError(
                f"Ollama rejected the request: {exc.response.text}"
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaUnavailableError("Unable to complete Ollama request") from exc

        message = data.get("message", {})
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise OllamaModelError("Ollama returned an invalid chat response")
        return message["content"]

    async def stream_chat(
        self,
        messages: list[ChatMessage],
        temperature: float,
        max_tokens: int | None,
    ) -> AsyncIterator[str]:
        payload = self._payload(messages, temperature, max_tokens, stream=True)
        try:
            async with httpx.AsyncClient(timeout=self.settings.ollama_timeout) as client:
                async with client.stream(
                    "POST", f"{self.settings.ollama_base_url}/api/chat", json=payload
                ) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                        except json.JSONDecodeError as exc:
                            raise OllamaModelError(
                                "Ollama returned invalid streaming data"
                            ) from exc
                        if data.get("error"):
                            raise OllamaModelError(str(data["error"]))
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield content
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("Ollama streaming request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaModelError(
                f"Ollama rejected the streaming request: {exc.response.text}"
            ) from exc
        except httpx.HTTPError as exc:
            raise OllamaUnavailableError(
                f"Unable to stream from Ollama at {self.settings.ollama_base_url}. "
                "Make sure Ollama is running and reachable."
            ) from exc
