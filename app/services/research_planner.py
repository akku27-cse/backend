from datetime import datetime, timezone

from app.schemas.agent import ResearchPlan, ResearchTask


class ResearchPlanner:
    """Creates a bounded, dependency-aware plan without inventing tool calls."""

    def build(self, execution_id: str, query: str, has_documents: bool) -> ResearchPlan:
        lowered = query.lower()
        tasks: list[ResearchTask] = []
        if any(term in lowered for term in ("latest", "current", "recent", "news", "today", "research")):
            tasks.append(ResearchTask(
                task_id="web-search",
                description=f"Find current sources relevant to: {query}",
                required_tool="web_search",
                parameters={"query": query},
                expected_output="Relevant titled search results with URLs and summaries",
            ))
        if has_documents and any(
            term in lowered for term in ("document", "pdf", "uploaded", "knowledge base", "compare")
        ):
            tasks.append(ResearchTask(
                task_id="rag-retrieval",
                description=f"Retrieve relevant uploaded-document evidence for: {query}",
                required_tool="rag_retrieval",
                parameters={"query": query},
                expected_output="Relevant document excerpts with page references",
            ))
        if any(term in lowered for term in ("calculator", "calculate", "current time", "text length")):
            tool_name = (
                "calculator" if any(term in lowered for term in ("calculator", "calculate"))
                else "current_time" if "time" in lowered
                else "text_length"
            )
            tasks.append(ResearchTask(
                task_id="mcp-tool",
                description=f"Execute the discovered MCP tool {tool_name}",
                required_tool="mcp",
                parameters={"tool_name": tool_name},
                expected_output="Verified MCP tool result",
            ))
        if not tasks:
            tasks.append(ResearchTask(
                task_id="local-reasoning",
                description="Answer the question with the local language model",
                required_tool="ollama",
                parameters={"query": query},
                expected_output="A direct local-model response",
            ))
        if any(term in lowered for term in ("detailed", "deep", "article", "sources")) and any(
            task.required_tool == "web_search" for task in tasks
        ):
            tasks.append(ResearchTask(
                task_id="web-extraction",
                description="Extract readable content from the strongest search results",
                required_tool="webpage_extraction",
                parameters={},
                expected_output="Clean webpage text for evidence",
                dependencies=["web-search"],
            ))
        return ResearchPlan(
            execution_id=execution_id,
            query=query,
            tasks=tasks,
            created_at=datetime.now(timezone.utc),
        )
