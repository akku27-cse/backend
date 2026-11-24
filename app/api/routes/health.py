from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.services.ollama_client import OllamaClient
from app.utils.exceptions import OllamaError

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {"status": "ok", "service": "the-omniscience-bound-backend"}


@router.get("/api/v1/ollama/status")
async def ollama_status(settings: Settings = Depends(get_settings)) -> dict:
    client = OllamaClient(settings)
    try:
        result = await client.status()
    except OllamaError as exc:
        return {
            "connected": False,
            "models": [],
            "model_available": False,
            "error": str(exc),
        }
    return result
