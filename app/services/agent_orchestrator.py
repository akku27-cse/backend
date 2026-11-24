import logging
from typing import Any

from app.core.config import Settings
from app.schemas.chat import ChatMessage
from app.schemas.hybrid import ExtractedPage, SearchResult, ToolExecutionResult
from app.services.mcp_client import MCPError, get_mcp_manager
from app.services.tool_registry import ToolRegistry
from app.services.ollama_client import OllamaClient
from app.services.tool_selector import ToolSelectionEngine
from app.services.web_search import SearchError, WebSearchService
from app.services.webpage_extractor import ExtractionError, WebpageExtractionService
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.search = WebSearchService(settings)
        self.extractor = WebpageExtractionService(settings)
        self.mcp = get_mcp_manager(settings)
        self.registry = ToolRegistry(self.mcp)
        self.selector = ToolSelectionEngine()
        self.ollama = OllamaClient(settings)
        self.rag = RAGService(settings)

    async def run(self, query: str, history: list[ChatMessage], temperature: float, max_tokens: int | None) -> tuple[str, list[str], list[str]]:
        if self._may_need_knowledge(query) and self.rag.has_documents():
            answer = await self.rag.answer(
                query,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            sources = [
                f"{chunk.document_name} (page {chunk.page_number})"
                for chunk in answer.sources
            ]
            return answer.response, sources, ["rag_retrieval"]
        if self._may_need_mcp(query):
            try:
                tools = await self.registry.list_tools()
            except MCPError as exc:
                logger.warning("MCP discovery skipped: %s", exc)
                tools = []
        else:
            tools = []
        decision = await self.selector.select_with_model(query, tools, self.ollama)
        search_results: list[SearchResult] = []
        pages: list[ExtractedPage] = []
        executions: list[ToolExecutionResult] = []
        if decision.search:
            try:
                search_results = await self.search.search(query)
            except SearchError as exc:
                logger.warning("Search skipped: %s", exc)
        if search_results and any(
            phrase in query.lower() for phrase in ("full article", "detailed", "read the result")
        ):
            try:
                pages.append(await self.extractor.extract(search_results[0].url))
            except ExtractionError as exc:
                logger.warning("Search-result extraction failed: %s", exc)
        for url in decision.extract_urls:
            try:
                pages.append(await self.extractor.extract(url))
            except ExtractionError as exc:
                logger.warning("Extraction failed for %s: %s", url, exc)
        for tool in decision.mcp_tools[: self.settings.max_tool_rounds]:
            result = await self.mcp.call_tool(tool, decision.mcp_arguments)
            executions.append(result)
        context = self._context(search_results, pages, executions)
        messages = list(history)
        if context:
            messages.append(ChatMessage(role="system", content=(
                "Use the following verified external context. Do not invent facts or tool outputs. "
                + ("Cite source URLs when using web context. " if search_results or pages else "")
                + "Do not invent URLs for MCP results.\n\n" + context
            )))
        messages.append(ChatMessage(role="user", content=query))
        response = await self.ollama.chat(messages, temperature, max_tokens)
        sources = [result.url for result in search_results] + [page.url for page in pages]
        used = (["web_search"] if search_results else []) + (["webpage_extraction"] if pages else [])
        used.extend(f"mcp:{result.tool}" for result in executions if result.success)
        return response, sources, used

    @staticmethod
    def _may_need_mcp(query: str) -> bool:
        lowered = query.lower()
        return any(
            term in lowered
            for term in (
                "mcp",
                "calculator",
                "calculate",
                "compute",
                "current time",
                "what time",
                "text length",
                "character count",
            )
        )

    @staticmethod
    def _may_need_knowledge(query: str) -> bool:
        lowered = query.lower()
        return any(
            phrase in lowered
            for phrase in (
                "uploaded document",
                "uploaded pdf",
                "my document",
                "my pdf",
                "in the document",
                "in the pdf",
                "according to the document",
                "according to the pdf",
                "knowledge base",
            )
        )

    @staticmethod
    def _context(search_results: list[SearchResult], pages: list[ExtractedPage], executions: list[ToolExecutionResult]) -> str:
        chunks: list[str] = []
        for result in search_results:
            description = result.description[:1500]
            chunks.append(f"SEARCH RESULT\nTitle: {result.title}\nURL: {result.url}\nSummary: {description}")
        for page in pages:
            chunks.append(
                f"WEBPAGE\nTitle: {page.title}\nURL: {page.url}\nContent: {page.content[:6000]}"
            )
        for execution in executions:
            chunks.append(f"MCP TOOL {execution.tool}\nResult: {execution.output if execution.success else execution.error}")
        return "\n\n".join(chunks)[:12000]
