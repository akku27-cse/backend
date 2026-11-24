from typing import Any

import httpx

from app.core.config import Settings
from app.utils.exceptions import OllamaModelError, OllamaTimeoutError, OllamaUnavailableError


class EmbeddingService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def embed(self, text: str) -> list[float]:
        payload = {"model": self.settings.embedding_model, "input": text}
        try:
            async with httpx.AsyncClient(timeout=self.settings.ollama_timeout) as client:
                response = await client.post(
                    f"{self.settings.ollama_base_url}/api/embed", json=payload
                )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except httpx.TimeoutException as exc:
            raise OllamaTimeoutError("Ollama embedding request timed out") from exc
        except httpx.HTTPStatusError as exc:
            raise OllamaModelError(
                f"Ollama rejected the embedding request: {exc.response.text}"
            ) from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise OllamaUnavailableError("Unable to generate Ollama embedding") from exc
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or not embeddings or not isinstance(embeddings[0], list):
            raise OllamaModelError("Ollama returned an invalid embedding response")
        return [float(value) for value in embeddings[0]]
