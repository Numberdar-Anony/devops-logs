from typing import List
from uuid import uuid4
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.session import get_db
from app.models.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisResult as AnalysisResultSchema,
    FindingRead,
    AnalysisSummary,
    AnalysisDetail,
    LogEntry,
    LogIngestResponse,
    IngestRequest,
)
from app.models.db_models import AnalysisResult, Finding, PersistedAnalysis, PersistedFinding, PersistedResource
from app.services.ingestion import global_log_buffer
from app.services.correlation import correlation_engine
from app.core.plugin_manager import plugin_manager
from app.services.ai import airca
from datetime import datetime, timezone
import json
from app.storage.s3 import storage
from app.celery_app import celery
try:
    from celery.result import AsyncResult
except ImportError:  # pragma: no cover - allow import without celery installed
    class AsyncResult:  # type: ignore
        def __init__(self, *_, **__):
            self.state = "PENDING"
            self.result = None
            self.info = None
from sqlalchemy import func

router = APIRouter()


@router.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/api/logs", response_model=LogIngestResponse)
async def ingest_logs(logs: List[LogEntry], db: AsyncSession = Depends(get_db)) -> LogIngestResponse:
    stored, size = await global_log_buffer.ingest(logs, db)
    await db.commit()
    return LogIngestResponse(stored=stored, buffer_size=size)


@router.post("/api/ingest")
async def ingest_v2(request: IngestRequest):
    # Convert logs to JSON string for storage
    raw_logs = json.dumps(request.logs, indent=2)
    
    # Save to MinIO
    filename = f"{request.source}/{request.service}/{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    storage.upload_raw_log(filename, raw_logs)
    
    # Queue Celery task
    # process_upload expects (file_text, source)
    task = celery.send_task("app.tasks.process_upload", args=[raw_logs, request.source])
    
    return {"job_id": task.id, "status": "queued"}


@router.get("/api/findings", response_model=List[FindingRead])
async def list_findings(limit: int = 100, db: AsyncSession = Depends(get_db)) -> List[FindingRead]:
    result = await db.execute(select(Finding).order_by(Finding.created_at.desc()).limit(limit))
    findings = result.scalars().all()
    return findings


@router.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest, db: AsyncSession = Depends(get_db)) -> AnalyzeResponse:
    logs = request.logs or global_log_buffer.snapshot()
    correlation_id, correlation_findings = correlation_engine.correlate(logs)
    correlation_id = request.correlation_id or correlation_id or str(uuid4())
    context = {"correlation_id": correlation_id}

    plugin_findings = await plugin_manager.run(logs, context)
    findings_to_store = correlation_findings + plugin_findings

    saved_findings: List[FindingRead] = []
    for finding in findings_to_store:
        record = Finding(
            plugin_name=finding.plugin_name,
            summary=finding.summary,
            details=finding.details,
            severity=finding.severity,
            source=finding.source or "unknown",
            correlation_id=finding.correlation_id or correlation_id,
        )
        db.add(record)
        await db.flush()
        await db.refresh(record)
        saved_findings.append(record)  # ORM object works with from_attributes
    await db.commit()

    if request.use_ai:
        try:
            analysis: AnalysisResultSchema = await airca.analyze(logs, correlation_id)
        except Exception as e:
            await db.rollback()
            raise HTTPException(status_code=500, detail=str(e)) from e
    else:
        analysis = AnalysisResultSchema(
            root_cause="AI analysis skipped",
            impact="Unknown",
            fix="Enable AI by setting use_ai=true",
            correlation_id=correlation_id,
        )

    analysis_record = AnalysisResult(
        root_cause=analysis.root_cause,
        impact=analysis.impact,
        fix=analysis.fix,
        correlation_id=correlation_id,
    )
    db.add(analysis_record)
    await db.flush() # flush to get ID and ensure no error before continuing
    await db.refresh(analysis_record)
    analysis.created_at = analysis_record.created_at

    # Persist normalized analysis to PostgreSQL/Neon
    print("structured_fix before save (analyze):", getattr(analysis, "structured_fix", None))
    final_analysis_id = correlation_id or f"ANL-{uuid4().hex[:6].upper()}"
    
    structured_fix_value = getattr(analysis, "structured_fix", None)
    if hasattr(structured_fix_value, "model_dump"):
        structured_fix_value = structured_fix_value.model_dump()
        
    persisted = PersistedAnalysis(
        analysis_id=final_analysis_id,
        source=logs[0].source if logs else None,
        severity=(findings_to_store[0].severity if findings_to_store else analysis.impact or "medium"),
        summary=analysis.root_cause or (findings_to_store[0].summary if findings_to_store else None),
        root_cause=analysis.root_cause,
        recommendation=analysis.fix,
        structured_fix=structured_fix_value,
        raw_response_json=None,
    )
    db.add(persisted)
    await db.flush()
    for f in findings_to_store:
        db.add(
            PersistedFinding(
                analysis_id=persisted.id,
                plugin=getattr(f, "plugin_name", None),
                title=f.summary,
                severity=f.severity,
                description=f.details,
            )
        )
    await db.commit()
    await db.refresh(persisted)

    response_payload = AnalyzeResponse(
        findings=saved_findings,
        analysis=analysis,
        correlation_id=correlation_id,
    )
    # store full response JSON if persisted exists
    try:
        if "persisted" in locals():
            persisted.raw_response_json = response_payload.model_dump()
            db.add(persisted)
            await db.commit()
    except Exception:
        await db.rollback()

    return response_payload


@router.post("/api/analyze/upload")
async def analyze_file(
    file: UploadFile = File(...),
    source: str = Form("auto"),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    text = content.decode("utf-8", errors="ignore")
    task = celery.send_task("app.tasks.process_upload", args=[text, source])
    return {"job_id": task.id, "status": "queued"}


@router.get("/api/jobs/{job_id}")
async def job_status(job_id: str):
    result = AsyncResult(job_id, app=celery)
    state = result.state
    normalized = state.lower() if isinstance(state, str) else state
    if normalized == "pending":
        normalized = "queued"
    response = {"job_id": job_id, "status": normalized}
    if state == "SUCCESS" and result.result:
        response["analysis_id"] = result.result.get("analysis_id")
        response["status"] = "completed"
    elif state == "FAILURE":
        response["status"] = "failed"
        response["error"] = str(result.result)
    elif result.info and isinstance(result.info, dict):
        response.update(result.info)
    return response


@router.get("/api/analyses", response_model=List[AnalysisSummary])
async def list_analyses(db: AsyncSession = Depends(get_db)) -> List[AnalysisSummary]:
    result = await db.execute(select(PersistedAnalysis).order_by(PersistedAnalysis.created_at.desc()).limit(50))
    return result.scalars().all()


@router.get("/api/analyses/{analysis_id}", response_model=AnalysisDetail)
async def get_analysis_detail(analysis_id: str, db: AsyncSession = Depends(get_db)) -> AnalysisDetail:
    result = await db.execute(
        select(PersistedAnalysis)
        .where(PersistedAnalysis.analysis_id == analysis_id)
        .options(selectinload(PersistedAnalysis.findings), selectinload(PersistedAnalysis.resources))
    )
    analysis_obj = result.scalars().first()
    if not analysis_obj:
        raise HTTPException(status_code=404, detail="Analysis not found")

    print("structured_fix in API response:", analysis_obj.structured_fix)

    structured_fix_response = analysis_obj.structured_fix
    if hasattr(structured_fix_response, "model_dump"):
        structured_fix_response = structured_fix_response.model_dump()

    return AnalysisDetail(
        analysis_id=analysis_obj.analysis_id,
        source=analysis_obj.source,
        severity=analysis_obj.severity,
        summary=analysis_obj.summary,
        root_cause=analysis_obj.root_cause,
        recommendation=analysis_obj.recommendation,
        created_at=analysis_obj.created_at,
        findings=analysis_obj.findings,
        affected_resources=analysis_obj.resources,
        raw_response_json=analysis_obj.raw_response_json,
        raw_logs=analysis_obj.raw_logs,
        structured_fix=structured_fix_response,
    )


@router.get("/api/metrics")
async def metrics(db: AsyncSession = Depends(get_db)) -> dict:
    total = await db.scalar(select(func.count(PersistedAnalysis.id)))

    severity_counts_rows = await db.execute(
        select(PersistedAnalysis.severity, func.count(PersistedAnalysis.id)).group_by(PersistedAnalysis.severity)
    )
    severity_counts = {s or "unknown": c for s, c in severity_counts_rows.all()}

    top_plugin_row = await db.execute(
        select(PersistedFinding.plugin, func.count(PersistedFinding.id))
        .group_by(PersistedFinding.plugin)
        .order_by(func.count(PersistedFinding.id).desc())
        .limit(1)
    )
    top_plugin_first = top_plugin_row.first()
    top_plugin = top_plugin_first[0] if top_plugin_first else None

    top_issue_row = await db.execute(
        select(PersistedFinding.title, func.count(PersistedFinding.id))
        .group_by(PersistedFinding.title)
        .order_by(func.count(PersistedFinding.id).desc())
        .limit(1)
    )
    top_issue_first = top_issue_row.first()
    top_issue = top_issue_first[0] if top_issue_first else None

    top_source_row = await db.execute(
        select(PersistedAnalysis.source, func.count(PersistedAnalysis.id))
        .group_by(PersistedAnalysis.source)
        .order_by(func.count(PersistedAnalysis.id).desc())
        .limit(1)
    )
    top_source_first = top_source_row.first()
    top_source = top_source_first[0] if top_source_first else None

    over_time_rows = await db.execute(
        select(func.date(PersistedAnalysis.created_at).label("date"), func.count(PersistedAnalysis.id))
        .group_by(func.date(PersistedAnalysis.created_at))
        .order_by(func.date(PersistedAnalysis.created_at))
        .limit(60)
    )
    analyses_over_time = [{"date": str(r[0]), "count": r[1]} for r in over_time_rows.all()]

    plugin_rows = await db.execute(
        select(PersistedFinding.plugin, func.count(PersistedFinding.id))
        .group_by(PersistedFinding.plugin)
        .order_by(func.count(PersistedFinding.id).desc())
    )
    plugin_counts = [{"plugin": r[0] or "unknown", "count": r[1]} for r in plugin_rows.all()]

    severity_distribution = [{"severity": k, "count": v} for k, v in severity_counts.items()]

    return {
        "total_analyses": total or 0,
        "critical": severity_counts.get("critical", 0),
        "high": severity_counts.get("high", 0),
        "medium": severity_counts.get("medium", 0),
        "low": severity_counts.get("low", 0),
        "top_plugin": top_plugin,
        "top_issue": top_issue,
        "top_source": top_source,
        "analyses_over_time": analyses_over_time,
        "plugin_counts": plugin_counts,
        "severity_distribution": severity_distribution,
    }
