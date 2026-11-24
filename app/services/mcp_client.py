import json
import logging
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
try:
    from mcp.client.streamable_http import streamable_http_client
    _STREAMABLE_HTTP_SUPPORTS_CLIENT = True
except ImportError:
    from mcp.client.streamable_http import streamablehttp_client

    streamable_http_client = streamablehttp_client
    _STREAMABLE_HTTP_SUPPORTS_CLIENT = False

from app.core.config import Settings
from app.schemas.hybrid import ToolExecutionResult, ToolInfo

logger = logging.getLogger(__name__)


class MCPError(Exception):
    """Raised for MCP configuration, connection, or protocol failures."""


@dataclass
class _Connection:
    name: str
    config: dict[str, Any]
    session: ClientSession


class MCPServerManager:
    """Manages official-SDK MCP sessions and the dynamically discovered tools."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._stack = AsyncExitStack()
        self._connections: dict[str, _Connection] = {}
        self._tools: dict[str, ToolInfo] = {}
        self._started = False

    def _servers(self) -> list[dict[str, Any]]:
        try:
            value = json.loads(self.settings.mcp_servers_json)
        except json.JSONDecodeError as exc:
            raise MCPError("MCP_SERVERS_JSON is not valid JSON") from exc
        if not isinstance(value, list):
            raise MCPError("MCP_SERVERS_JSON must be a JSON array")
        return [item for item in value if isinstance(item, dict) and item.get("name")]

    async def connect_all(self) -> dict[str, str]:
        if self._started:
            return {name: "connected" for name in self._connections}
        self._started = True
        statuses: dict[str, str] = {}
        for config in self._servers():
            name = str(config["name"])
            try:
                await self.connect(name, config)
                statuses[name] = "connected"
            except (MCPError, OSError, httpx.HTTPError) as exc:
                statuses[name] = f"error: {exc}"
                logger.warning("MCP server %s unavailable: %s", name, exc)
        return statuses

    async def connect(self, name: str, config: dict[str, Any] | None = None) -> None:
        if name in self._connections:
            return
        config = config or next((item for item in self._servers() if item["name"] == name), None)
        if not config:
            raise MCPError(f"MCP server '{name}' is not configured")
        transport = str(config.get("transport", "stdio")).lower()
        if transport == "stdio":
            command = config.get("command")
            if not isinstance(command, str) or not command:
                raise MCPError(f"MCP server '{name}' requires a command")
            environment = os.environ.copy()
            configured_env = config.get("env", {})
            if isinstance(configured_env, dict):
                environment.update({str(key): str(value) for key, value in configured_env.items()})
            read_stream, write_stream = await self._stack.enter_async_context(
                stdio_client(StdioServerParameters(
                    command=command,
                    args=[str(arg) for arg in config.get("args", [])],
                    env=environment,
                    cwd=config.get("cwd") or str(Path.cwd()),
                ))
            )
        elif transport in {"streamable-http", "http"}:
            url = config.get("url")
            if not isinstance(url, str) or not url:
                raise MCPError(f"MCP server '{name}' requires a URL")
            headers = {
                str(k): str(v) for k, v in config.get("headers", {}).items()
            }
            if _STREAMABLE_HTTP_SUPPORTS_CLIENT:
                client = httpx.AsyncClient(
                    timeout=self.settings.mcp_timeout, headers=headers
                )
                await self._stack.enter_async_context(client)
                read_stream, write_stream, _ = await self._stack.enter_async_context(
                    streamable_http_client(url, http_client=client)
                )
            else:
                read_stream, write_stream, _ = await self._stack.enter_async_context(
                    streamable_http_client(
                        url, headers=headers, timeout=self.settings.mcp_timeout
                    )
                )
        else:
            raise MCPError(f"Unsupported MCP transport '{transport}'")
        session = await self._stack.enter_async_context(
            ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timedelta(seconds=self.settings.mcp_timeout),
            )
        )
        await session.initialize()
        connection = _Connection(name=name, config=config, session=session)
        self._connections[name] = connection
        await self._discover(connection)

    async def _discover(self, connection: _Connection) -> None:
        result = await connection.session.list_tools()
        for tool in result.tools:
            key = f"{connection.name}:{tool.name}"
            schema = tool.inputSchema if isinstance(tool.inputSchema, dict) else {}
            self._tools[key] = ToolInfo(
                name=tool.name,
                description=tool.description or "",
                input_schema=schema,
                server=connection.name,
                tool_type="mcp",
                available=True,
            )

    async def refresh(self) -> list[ToolInfo]:
        await self.connect_all()
        self._tools.clear()
        for connection in self._connections.values():
            try:
                await self._discover(connection)
            except Exception as exc:
                logger.warning("MCP tool refresh failed for %s: %s", connection.name, exc)
        return list(self._tools.values())

    async def list_tools(self) -> list[ToolInfo]:
        await self.connect_all()
        return list(self._tools.values())

    def statuses(self) -> dict[str, str]:
        configured = {str(item["name"]): "disconnected" for item in self._servers()}
        configured.update({name: "connected" for name in self._connections})
        return configured

    async def call_tool(self, tool: ToolInfo, arguments: dict[str, Any]) -> ToolExecutionResult:
        connection = self._connections.get(tool.server)
        if not connection:
            return ToolExecutionResult(
                tool=tool.name, server=tool.server, success=False, error="MCP server is not connected"
            )
        validation_error = _validate_arguments(tool.input_schema, arguments)
        if validation_error:
            return ToolExecutionResult(tool=tool.name, server=tool.server, success=False, error=validation_error)
        try:
            result = await connection.session.call_tool(
                tool.name,
                arguments,
                read_timeout_seconds=timedelta(seconds=self.settings.mcp_timeout),
            )
            output = [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in result.content
            ]
            if result.structuredContent:
                output.append(result.structuredContent)
            return ToolExecutionResult(
                tool=tool.name,
                server=tool.server,
                success=not result.isError,
                output=output,
                error="MCP tool returned an error" if result.isError else None,
            )
        except Exception as exc:
            logger.warning("MCP tool execution failed for %s:%s: %s", tool.server, tool.name, exc)
            return ToolExecutionResult(tool=tool.name, server=tool.server, success=False, error=str(exc))

    async def close(self) -> None:
        try:
            await self._stack.aclose()
        except RuntimeError as exc:
            logger.warning("MCP connection cleanup did not complete cleanly: %s", exc)
        self._connections.clear()
        self._tools.clear()
        self._started = False

    async def disconnect(self, name: str) -> None:
        if name not in self._connections:
            return
        await self.close()


@lru_cache
def get_mcp_manager(settings: Settings) -> MCPServerManager:
    return MCPServerManager(settings)


def _validate_arguments(schema: dict[str, Any], arguments: dict[str, Any]) -> str | None:
    required = schema.get("required", [])
    missing = [str(name) for name in required if name not in arguments]
    if missing:
        return f"Missing required MCP arguments: {', '.join(missing)}"
    properties = schema.get("properties", {})
    if isinstance(properties, dict):
        unknown = [name for name in arguments if name not in properties]
        if unknown:
            return f"Unknown MCP arguments: {', '.join(unknown)}"
    return None
