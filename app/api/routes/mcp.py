from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.schemas.hybrid import ToolInfo
from app.services.mcp_client import get_mcp_manager

router = APIRouter(prefix="/api/v1/mcp", tags=["mcp"])


@router.get("/servers")
async def mcp_servers(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    manager = get_mcp_manager(settings)
    await manager.connect_all()
    return manager.statuses()


@router.get("/tools", response_model=list[ToolInfo])
async def mcp_tools(settings: Settings = Depends(get_settings)) -> list[ToolInfo]:
    manager = get_mcp_manager(settings)
    return await manager.list_tools()


@router.post("/refresh", response_model=list[ToolInfo])
async def refresh_mcp_tools(settings: Settings = Depends(get_settings)) -> list[ToolInfo]:
    manager = get_mcp_manager(settings)
    return await manager.refresh()


@router.post("/connect/{server_name}")
async def connect_mcp_server(
    server_name: str, settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    manager = get_mcp_manager(settings)
    try:
        await manager.connect(server_name)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"server": server_name, "status": "connected"}


@router.post("/disconnect/{server_name}")
async def disconnect_mcp_server(
    server_name: str, settings: Settings = Depends(get_settings)
) -> dict[str, str]:
    await get_mcp_manager(settings).disconnect(server_name)
    return {"server": server_name, "status": "disconnected"}


@router.post("/execute/{server_name}/{tool_name}")
async def execute_mcp_tool(
    server_name: str,
    tool_name: str,
    arguments: dict[str, Any],
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    manager = get_mcp_manager(settings)
    tools = await manager.list_tools()
    tool = next(
        (item for item in tools if item.server == server_name and item.name == tool_name),
        None,
    )
    if not tool:
        raise HTTPException(status_code=404, detail="MCP tool was not discovered")
    result = await manager.call_tool(tool, arguments)
    return result.model_dump()
