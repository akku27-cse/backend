from datetime import datetime, timezone
from hashlib import sha256
from uuid import uuid4

from app.schemas.agent import EvidenceRecord


class EvidenceCollector:
    def __init__(self, execution_id: str, query: str):
        self.execution_id = execution_id
        self.query = query
        self._fingerprints: set[str] = set()
        self.records: list[EvidenceRecord] = []

    def add(
        self,
        task_id: str,
        source_type: str,
        source_title: str,
        excerpt: str,
        tool_name: str,
        source_url: str | None = None,
        metadata: dict | None = None,
        source_reference: str = "",
    ) -> EvidenceRecord | None:
        fingerprint = sha256(
            f"{source_type}|{source_url}|{source_title}|{excerpt}".encode()
        ).hexdigest()
        if fingerprint in self._fingerprints:
            return None
        self._fingerprints.add(fingerprint)
        record = EvidenceRecord(
            evidence_id=str(uuid4()),
            execution_id=self.execution_id,
            task_id=task_id,
            query=self.query,
            source_type=source_type,
            source_title=source_title,
            source_url=source_url,
            excerpt=excerpt,
            retrieved_at=datetime.now(timezone.utc),
            tool_name=tool_name,
            metadata=metadata or {},
            source_reference=source_reference or source_url or source_title,
        )
        self.records.append(record)
        return record
