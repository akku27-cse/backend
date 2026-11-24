import logging
from typing import Any

import httpx

from app.core.config import Settings
from app.schemas.hybrid import SearchResult

logger = logging.getLogger(__name__)


class SearchError(Exception):
    """Raised when a configured search provider cannot complete a request."""


class WebSearchService:
    """Provider-neutral search facade with Tavily as the built-in provider."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def search(self, query: str, count: int | None = None) -> list[SearchResult]:
        if not self.settings.search_api_key:
            raise SearchError("SEARCH_API_KEY is not configured")
        if self.settings.search_provider != "tavily":
            raise SearchError(
                f"Unsupported SEARCH_PROVIDER '{self.settings.search_provider}'"
            )
        payload = {
            "query": query,
            "max_results": count or self.settings.search_result_count,
            "include_answer": False,
            "include_raw_content": False,
        }
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.settings.search_api_key}",
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.search_timeout) as client:
                response = await client.post(
                    self.settings.search_endpoint, json=payload, headers=headers
                )
                response.raise_for_status()
                data = response.json()
        except httpx.TimeoutException as exc:
            raise SearchError("Web search timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise SearchError(f"Web search failed: {exc}") from exc

        results: list[SearchResult] = []
        for item in data.get("results", []):
            if not isinstance(item, dict) or not item.get("url") or not item.get("title"):
                continue
            metadata: dict[str, Any] = {}
            for key in ("score", "published_date", "raw_content"):
                if key in item:
                    metadata[key] = item[key]
            results.append(
                SearchResult(
                    title=str(item["title"]),
                    url=str(item["url"]),
                    description=str(item.get("content", "")),
                    metadata=metadata,
                )
            )
        return results
