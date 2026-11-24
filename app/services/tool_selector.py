import re
import json
from dataclasses import dataclass, field

from app.schemas.chat import ChatMessage
from app.schemas.hybrid import ToolInfo

CURRENT_TERMS = ("latest", "current", "today", "recent", "news", "live", "price", "weather", "2026")


@dataclass
class ToolDecision:
    search: bool = False
    extract_urls: list[str] = field(default_factory=list)
    mcp_tools: list[ToolInfo] = field(default_factory=list)
    mcp_arguments: dict[str, object] = field(default_factory=dict)


class ToolSelectionEngine:
    """Deterministic, validated routing that avoids invented tool calls."""

    def select(self, query: str, available_tools: list[ToolInfo]) -> ToolDecision:
        lowered = query.lower()
        urls = re.findall(r"https?://[^\s<>\"]+", query)
        needs_search = any(term in lowered for term in CURRENT_TERMS) or any(
            phrase in lowered for phrase in ("search the web", "look up online", "find online")
        )
        needs_extract = bool(urls) or any(
            phrase in lowered for phrase in ("read this page", "summarize this article", "from the link")
        )
        selected_mcp = [
            tool for tool in available_tools
            if tool.name.lower() in lowered
            or tool.name == "calculator" and any(word in lowered for word in ("calculate", "compute", "math"))
            or tool.name == "current_time" and any(word in lowered for word in ("time", "date"))
            or tool.name == "text_length" and any(word in lowered for word in ("length", "characters"))
        ]
        arguments: dict[str, object] = {}
        match = re.search(r"\{.*\}", query)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, dict):
                    arguments = parsed
            except json.JSONDecodeError:
                pass
        return ToolDecision(
            search=needs_search and not urls,
            extract_urls=urls if needs_extract else [],
            mcp_tools=selected_mcp[:3],
            mcp_arguments=arguments,
        )

    async def select_with_model(self, query: str, available_tools: list[ToolInfo], ollama) -> ToolDecision:
        """Ask Qwen for JSON routing, then enforce the registry and schema locally."""
        fallback = self.select(query, available_tools)
        descriptions = [
            {
                "name": tool.name,
                "server": tool.server,
                "type": tool.tool_type,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in available_tools
        ]
        prompt = (
            "Return JSON only with keys search (boolean), extract_urls (array of strings), "
            "mcp_tool (string or null), mcp_server (string or null), and arguments (object). "
            "Select only a listed tool. Use no tool when unnecessary.\n"
            f"TOOLS:\n{json.dumps(descriptions)}\nQUERY:\n{query}"
        )
        try:
            raw = await ollama.chat(
                [
                    ChatMessage(role="system", content="You are a strict tool router. Output valid JSON only."),
                    ChatMessage(role="user", content=prompt),
                ],
                0.0,
                256,
            )
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            decision = json.loads(match.group(0)) if match else {}
            name = decision.get("mcp_tool")
            server = decision.get("mcp_server")
            allowed = next(
                (tool for tool in available_tools if tool.name == name and tool.server == server),
                None,
            )
            return ToolDecision(
                search=bool(decision.get("search")),
                extract_urls=[
                    url for url in decision.get("extract_urls", [])
                    if isinstance(url, str) and url.startswith(("http://", "https://"))
                ],
                mcp_tools=[allowed] if allowed else fallback.mcp_tools,
                mcp_arguments=decision.get("arguments", {}) if isinstance(decision.get("arguments", {}), dict) else fallback.mcp_arguments,
            )
        except (ValueError, TypeError, KeyError):
            return fallback
