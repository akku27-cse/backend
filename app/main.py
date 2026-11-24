import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import agent, chat, health, mcp, rag
from app.core.config import get_settings
from app.services.mcp_client import get_mcp_manager

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    if settings.mcp_auto_connect:
        await get_mcp_manager(settings).connect_all()
    yield
    await get_mcp_manager(settings).close()


app = FastAPI(title="The Omniscience Bound", version="1.0.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(chat.router)
app.include_router(mcp.router)
app.include_router(rag.router)
app.include_router(agent.router)
