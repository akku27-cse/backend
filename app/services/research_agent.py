import asyncio
import logging
from datetime import datetime, timezone

from app.core.config import Settings
from app.schemas.agent import ExecutionState, ResearchExecution, TaskStatus
from app.schemas.chat import ChatMessage
from app.services.agent_state import state_store
from app.services.evidence_collector import EvidenceCollector
from app.services.ollama_client import OllamaClient
from app.services.rag_service import RAGService
from app.services.research_planner import ResearchPlanner
from app.services.web_search import SearchError, WebSearchService
from app.services.webpage_extractor import ExtractionError, WebpageExtractionService
from app.services.mcp_client import MCPError, get_mcp_manager
from app.utils.exceptions import OllamaError

logger = logging.getLogger(__name__)


class ResearchAgent:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.planner = ResearchPlanner()
        self.search = WebSearchService(settings)
        self.extractor = WebpageExtractionService(settings)
        self.rag = RAGService(settings)
        self.ollama = OllamaClient(settings)
        self.mcp = get_mcp_manager(settings)

    async def start(self, query: str) -> ResearchExecution:
        execution = await state_store.create(query)
        asyncio.create_task(self._run(execution.execution_id))
        return execution

    async def _run(self, execution_id: str) -> None:
        execution = await state_store.get(execution_id)
        if not execution:
            return
        try:
            execution.state = ExecutionState.PLANNING
            await state_store.update(execution)
            plan = self.planner.build(
                execution_id, execution.query, self.rag.has_documents()
            )
            execution.plan = plan
            execution.state = ExecutionState.EXECUTING
            await state_store.update(execution)
            collector = EvidenceCollector(execution_id, execution.query)
            for index, task in enumerate(plan.tasks):
                if index >= self.settings.agent_max_steps:
                    task.status = TaskStatus.SKIPPED
                    task.error = "Maximum agent steps reached"
                    continue
                execution.current_task_id = task.task_id
                task.status = TaskStatus.RUNNING
                execution.state = (
                    ExecutionState.TOOL_CALLING
                    if task.required_tool != "ollama"
                    else ExecutionState.EXECUTING
                )
                await state_store.update(execution)
                try:
                    if task.required_tool == "web_search":
                        results = await asyncio.wait_for(
                            self.search.search(execution.query),
                            timeout=self.settings.agent_timeout,
                        )
                        task.result = [item.model_dump() for item in results]
                        for item in results:
                            collector.add(
                                task.task_id, "Web", item.title, item.description,
                                "tavily", item.url, item.metadata, item.url,
                            )
                        execution.tool_results.append({"task_id": task.task_id, "count": len(results)})
                    elif task.required_tool == "rag_retrieval":
                        chunks = await self.rag.search(execution.query)
                        task.result = [item.model_dump() for item in chunks]
                        for item in chunks:
                            collector.add(
                                task.task_id, "RAG", item.document_name, item.text,
                                "chroma", metadata=item.metadata,
                                source_reference=f"{item.document_name}:page:{item.page_number}",
                            )
                    elif task.required_tool == "webpage_extraction":
                        await self._extract_search_pages(execution, collector, task)
                    elif task.required_tool == "mcp":
                        tools = await self.mcp.list_tools()
                        tool = next(
                            (
                                item for item in tools
                                if item.name == task.parameters.get("tool_name")
                            ),
                            None,
                        )
                        if not tool:
                            raise MCPError("Required MCP tool was not discovered")
                        arguments = self._mcp_arguments(task.parameters.get("tool_name", ""), execution.query)
                        result = await self.mcp.call_tool(tool, arguments)
                        if not result.success:
                            raise MCPError(result.error or "MCP tool execution failed")
                        task.result = result.model_dump()
                        collector.add(
                            task.task_id, "MCP", tool.name, str(result.output),
                            f"mcp:{tool.name}", metadata={"server": tool.server},
                            source_reference=f"mcp:{tool.server}:{tool.name}",
                        )
                        execution.tool_results.append({"task_id": task.task_id, "tool": tool.name})
                    else:
                        task.result = await self.ollama.chat(
                            [ChatMessage(role="user", content=execution.query)],
                            0.2,
                            512,
                        )
                    task.status = TaskStatus.COMPLETED
                    execution.completed_tasks.append(task.task_id)
                except (
                    SearchError,
                    ExtractionError,
                    MCPError,
                    OllamaError,
                    asyncio.TimeoutError,
                    ValueError,
                    RuntimeError,
                ) as exc:
                    logger.exception("Research task failed: %s", task.task_id)
                    task.status = TaskStatus.FAILED
                    task.error = str(exc)
                    execution.failed_tasks.append(task.task_id)
                await state_store.update(execution)

            execution.state = ExecutionState.EVIDENCE_COLLECTING
            execution.evidence = collector.records
            await state_store.update(execution)
            execution.state = ExecutionState.SYNTHESIZING
            context = "\n\n".join(
                f"[{item.source_reference}] {item.excerpt[:3000]}"
                for item in collector.records
            )
            execution.response = await self.ollama.chat(
                [ChatMessage(
                    role="user",
                    content=(
                        "Synthesize a concise, evidence-aware answer. Use only the "
                        "evidence below, identify uncertainty, and cite source references.\n\n"
                        f"EVIDENCE:\n{context or '(No external evidence was collected.)'}\n\n"
                        f"QUESTION:\n{execution.query}"
                    ),
                )],
                0.2,
                1024,
            )
            execution.state = ExecutionState.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            await state_store.update(execution)
        except Exception as exc:
            logger.exception("Research execution failed: %s", execution_id)
            execution.state = ExecutionState.FAILED
            execution.error = str(exc)
            await state_store.update(execution)

    @staticmethod
    def _mcp_arguments(tool_name: str, query: str) -> dict:
        if tool_name == "calculator":
            expression = query.lower().split("calculate", 1)[-1].strip()
            return {"expression": expression or "0"}
        if tool_name == "text_length":
            return {"text": query}
        return {}

    async def _extract_search_pages(self, execution, collector, task) -> None:
        prior = next(
            (item for item in execution.plan.tasks if item.task_id == "web-search"),
            None,
        )
        if not prior or not isinstance(prior.result, list):
            raise ExtractionError("No web search results available for extraction")
        for item in prior.result[:3]:
            page = await self.extractor.extract(item["url"])
            collector.add(
                task.task_id, "Web", page.title, page.content[:6000],
                "webpage_extraction", page.url, page.metadata, page.url,
            )
