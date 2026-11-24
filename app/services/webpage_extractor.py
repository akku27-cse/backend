import logging
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup

from app.core.config import Settings
from app.schemas.hybrid import ExtractedPage

logger = logging.getLogger(__name__)


class ExtractionError(Exception):
    """Raised when a URL cannot be fetched or converted to useful text."""


class WebpageExtractionService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def extract(self, url: str) -> ExtractedPage:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ExtractionError("Only valid http(s) URLs can be extracted")
        try:
            async with httpx.AsyncClient(
                timeout=self.settings.extraction_timeout,
                follow_redirects=True,
                headers={"User-Agent": "The-Omniscience-Bound/2.0"},
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ExtractionError("Webpage request timed out") from exc
        except httpx.HTTPError as exc:
            raise ExtractionError(f"Unable to retrieve webpage: {exc}") from exc

        soup = BeautifulSoup(response.text, "html.parser")
        for element in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
            element.decompose()
        title = soup.title.get_text(" ", strip=True) if soup.title else ""
        main = soup.find("main") or soup.find("article") or soup.body or soup
        content = " ".join(main.get_text(" ", strip=True).split())
        if not content:
            raise ExtractionError("No readable text was found at the URL")
        metadata = {
            str(tag.get("name")): str(tag.get("content", ""))
            for tag in soup.find_all("meta")
            if tag.get("name") and tag.get("content")
        }
        return ExtractedPage(
            url=str(response.url),
            title=title,
            content=content[: self.settings.extraction_max_chars],
            metadata=metadata,
        )
