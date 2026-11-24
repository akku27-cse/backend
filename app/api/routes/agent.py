from fastapi import APIRouter, Depends, HTTPException

from app.core.config import Settings, get_settings
from app.schemas.agent import (
    ResearchAccepted,
    ResearchExecution,
    ResearchPlan,
    ResearchRequest,
    EvidenceRecord,
)
from app.services.agent_state import state_store
from app.services.research_agent import ResearchAgent

router = APIRouter(prefix="/api/agent", tags=["agent"])


async def _get_execution(execution_id: str) -> ResearchExecution:
    execution = await state_store.get(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Research execution not found")
    return execution


@router.post("/research", response_model=ResearchAccepted, status_code=202)
async def start_research(
    request: ResearchRequest, settings: Settings = Depends(get_settings)
) -> ResearchAccepted:
    execution = await ResearchAgent(settings).start(request.query)
    return ResearchAccepted(execution_id=execution.execution_id, state=execution.state)


@router.get("/status/{execution_id}", response_model=ResearchExecution)
async def research_status(execution_id: str) -> ResearchExecution:
    return await _get_execution(execution_id)


@router.get("/plan/{execution_id}", response_model=ResearchPlan | None)
async def research_plan(execution_id: str) -> ResearchPlan | None:
    return (await _get_execution(execution_id)).plan


@router.get("/evidence/{execution_id}", response_model=list[EvidenceRecord])
async def research_evidence(execution_id: str) -> list[EvidenceRecord]:
    return (await _get_execution(execution_id)).evidence


@router.get("/result/{execution_id}", response_model=ResearchExecution)
async def research_result(execution_id: str) -> ResearchExecution:
    return await _get_execution(execution_id)
