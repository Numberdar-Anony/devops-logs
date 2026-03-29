from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Iterable, List
from app.models.schemas import LogEntry, FindingCreate


class BasePlugin(ABC):
    name: str
    supported_sources: Iterable[str]

    @abstractmethod
    async def run(self, logs: List[LogEntry], context: Dict) -> List[FindingCreate]:
        ...
