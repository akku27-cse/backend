from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExecutionState(str, Enum):
    IDLE = "IDLE"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    TOOL_CALLING = "TOOL_CALLING"
    EVIDENCE_COLLECTING = "EVIDENCE_COLLECTING"
    SYNTHESIZING = "SYNTHESIZING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class ResearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=100_000)


class ResearchTask(BaseModel):
    task_id: str
    description: str
    required_tool: str
    parameters: dict[str, Any] = Field(default_factory=dict)
    expected_output: str
    dependencies: list[str] = Field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None


class ResearchPlan(BaseModel):
    execution_id: str
    query: str
    tasks: list[ResearchTask]
    created_at: datetime


class EvidenceRecord(BaseModel):
    evidence_id: str
    execution_id: str
    task_id: str
    query: str
    source_type: str
    source_title: str
    source_url: str | None = None
    excerpt: str
    retrieved_at: datetime
    tool_name: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_reference: str


class ResearchExecution(BaseModel):
    execution_id: str
    query: str
    state: ExecutionState = ExecutionState.IDLE
    plan: ResearchPlan | None = None
    current_task_id: str | None = None
    completed_tasks: list[str] = Field(default_factory=list)
    failed_tasks: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRecord] = Field(default_factory=list)
    tool_results: list[dict[str, Any]] = Field(default_factory=list)
    response: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None


class ResearchAccepted(BaseModel):
    execution_id: str
    state: ExecutionState
