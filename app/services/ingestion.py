from __future__ import annotations
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.schemas import LogEntry
from app.models.db_models import LogRecord
from app.core.config import settings


class LogIngestionService:
    def __init__(self, max_size: int = 5000, retention_minutes: int = 180):
        self.buffer: deque[LogEntry] = deque(maxlen=max_size)
        self.retention = timedelta(minutes=retention_minutes)

    async def ingest(self, logs: List[LogEntry], db: AsyncSession | None = None) -> Tuple[int, int]:
        now = datetime.now(timezone.utc)
        for log in logs:
            self.buffer.append(log)
            if db:
                record = LogRecord(
                    source=log.source,
                    service=log.service or log.metadata.get("service"),
                    level=log.level,
                    message=log.message,
                    timestamp=log.timestamp,
                    # Use JSON-safe serialization so datetimes become isoformat strings
                    raw=log.model_dump(mode="json"),
                )
                db.add(record)
        if db:
            await db.commit()
        self._trim(now)
        return len(logs), len(self.buffer)

    def snapshot(self) -> List[LogEntry]:
        return list(self.buffer)

    def _trim(self, now: datetime) -> None:
        cutoff = now - self.retention
        filtered = [log for log in self.buffer if log.timestamp >= cutoff]
        self.buffer = deque(filtered, maxlen=self.buffer.maxlen)
global_log_buffer = LogIngestionService(
    max_size=settings.log_buffer_size, retention_minutes=settings.log_retention_minutes
)
