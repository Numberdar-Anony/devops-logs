from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class LogEntry(BaseModel):
    source: Literal["jenkins", "kubernetes", "terraform", "argocd"]
    service: Optional[str] = Field(default=None, description="Service/component emitting the log")
    level: Optional[str] = Field(default=None)
    message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LogIngestResponse(BaseModel):
    stored: int
    buffer_size: int


class FindingCreate(BaseModel):
    plugin_name: str
    summary: str
    details: str
    severity: str = "medium"
    source: Optional[str] = None
    correlation_id: Optional[str] = None
    line_number: Optional[int] = None


class FindingRead(FindingCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AnalysisResult(BaseModel):
    root_cause: str
    impact: str
    fix: str
    correlation_id: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AnalyzeRequest(BaseModel):
    logs: Optional[List[LogEntry]] = None
    correlation_id: Optional[str] = None
    use_ai: bool = True


class AnalyzeResponse(BaseModel):
    findings: List[FindingRead]
    analysis: Optional[AnalysisResult]
    correlation_id: Optional[str]


class FindingItem(BaseModel):
    plugin: Optional[str] = None
    title: str
    severity: str
    description: str
    line_number: Optional[int] = None

    model_config = {"from_attributes": True}


class AffectedResourceItem(BaseModel):
    name: str
    type: str
    risk: float
    plugin: Optional[str] = None

    model_config = {"from_attributes": True}


class AnalysisSummary(BaseModel):
    analysis_id: str
    source: Optional[str]
    severity: Optional[str]
    summary: Optional[str]
    created_at: Optional[datetime]

    model_config = {"from_attributes": True}


class AnalysisDetail(AnalysisSummary):
    root_cause: Optional[str]
    recommendation: Optional[str]
    findings: List[FindingItem] = []
    affected_resources: List[AffectedResourceItem] = []
    raw_response_json: Optional[Dict[str, Any]] = None
    raw_logs: Optional[str] = None
