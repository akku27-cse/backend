import logging
from collections import defaultdict
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.core.config import Settings, get_settings
from app.schemas.chat import ChatMessage, ChatRequest, ChatResponse, ResetResponse
from app.services.agent_orchestrator import AgentOrchestrator
from app.services.ollama_client import OllamaClient
from app.utils.exceptions import (
    OllamaModelError,
    OllamaTimeoutError,
    OllamaUnavailableError,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])
_sessions: dict[str, list] = defaultdict(list)


def _messages(request: ChatRequest) -> list[ChatMessage]:
    messages = list(request.history)
    if request.session_id:
        messages = list(_sessions[request.session_id]) + messages
    messages.append(ChatMessage(role="user", content=request.message))
    return messages


def _raise_http_error(exc: Exception) -> None:
    if isinstance(exc, OllamaTimeoutError):
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    if isinstance(exc, OllamaUnavailableError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest, settings: Settings = Depends(get_settings)
) -> ChatResponse:
    session_id = request.session_id or str(uuid4())
    messages = _messages(request)
    client = OllamaClient(settings)
    try:
        response, sources, tools_used = await AgentOrchestrator(settings).run(
            request.message,
            messages[:-1],
            request.temperature,
            request.max_tokens,
        )
    except (OllamaModelError, OllamaTimeoutError, OllamaUnavailableError) as exc:
        _raise_http_error(exc)
    if request.session_id:
        _sessions[session_id].extend(
            [
                ChatMessage(role="user", content=request.message),
                ChatMessage(role="assistant", content=response),
            ]
        )
    return ChatResponse(
        response=response,
        model=settings.ollama_model,
        session_id=session_id,
        sources=sources,
        tools_used=tools_used,
    )


@router.post("/stream")
async def chat_stream(
    request: ChatRequest, settings: Settings = Depends(get_settings)
) -> StreamingResponse:
    session_id = request.session_id or str(uuid4())
    messages = _messages(request)
    client = OllamaClient(settings)

    async def generate():
        try:
            async for chunk in client.stream_chat(
                messages, request.temperature, request.max_tokens
            ):
                yield chunk
        except (OllamaModelError, OllamaTimeoutError, OllamaUnavailableError) as exc:
            logger.error("Streaming chat failed: %s", exc, exc_info=True)
            yield f"\n[ERROR] {exc}"

    return StreamingResponse(
        generate(),
        media_type="text/plain",
        headers={"X-Session-Id": session_id},
    )


@router.post("/reset", response_model=ResetResponse)
async def reset_chat(
    session_id: str, settings: Settings = Depends(get_settings)
) -> ResetResponse:
    _sessions.pop(session_id, None)
    return ResetResponse(message="Conversation history reset", session_id=session_id)
