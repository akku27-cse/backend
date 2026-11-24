from app.schemas.hybrid import ToolInfo
from app.services.mcp_client import MCPServerManager


class ToolRegistry:
    """Unified registry for native capabilities and dynamically discovered MCP tools."""

    def __init__(self, mcp_manager: MCPServerManager):
        self.mcp_manager = mcp_manager

    async def list_tools(self) -> list[ToolInfo]:
        tools = [
            ToolInfo(
                name="web_search",
                description="Search the internet for current information.",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}},
                tool_type="native",
            ),
            ToolInfo(
                name="webpage_extraction",
                description="Extract readable text from a webpage URL.",
                input_schema={"type": "object", "properties": {"url": {"type": "string"}}},
                tool_type="native",
            ),
        ]
        return tools + await self.mcp_manager.list_tools()
