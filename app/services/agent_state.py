import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.agent import ExecutionState, ResearchExecution


class AgentStateStore:
    """Bounded in-memory execution state store for the current backend process."""

    def __init__(self):
        self._items: dict[str, ResearchExecution] = {}
        self._lock = asyncio.Lock()

    async def create(self, query: str) -> ResearchExecution:
        now = datetime.now(timezone.utc)
        item = ResearchExecution(
            execution_id=str(uuid4()), query=query, created_at=now, updated_at=now
        )
        async with self._lock:
            self._items[item.execution_id] = item
        return item

    async def get(self, execution_id: str) -> ResearchExecution | None:
        async with self._lock:
            return self._items.get(execution_id)

    async def update(self, execution: ResearchExecution) -> ResearchExecution:
        execution.updated_at = datetime.now(timezone.utc)
        async with self._lock:
            self._items[execution.execution_id] = execution
        return execution


state_store = AgentStateStore()
