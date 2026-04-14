import json
import asyncio
from datetime import datetime, timezone
from app.celery_app import celery
from app.models.schemas import LogEntry
from app.services.correlation import correlation_engine
from app.core.plugin_manager import plugin_manager
from app.services.ai import airca
from app.db.session import AsyncSessionLocal
from app.models.db_models import (
    Finding,
    AnalysisResult,
    PersistedAnalysis,
    PersistedFinding,
)


async def run_analysis_pipeline(logs, raw_text: str | None = None):
    async with AsyncSessionLocal() as db:
        try:
            correlation_id, correlation_findings = correlation_engine.correlate(logs)
            correlation_id = correlation_id or f"ANL-{datetime.now(timezone.utc).strftime('%H%M%S')}"
            context = {"correlation_id": correlation_id}

            plugin_findings = await plugin_manager.run(logs, context)
            findings_to_store = correlation_findings + plugin_findings

            saved_findings = []
            for f in findings_to_store:
                record = Finding(
                    plugin_name=f.plugin_name,
                    summary=f.summary,
                    details=f.details,
                    severity=f.severity,
                    source=f.source or "unknown",
                    correlation_id=correlation_id,
                )
                db.add(record)
                saved_findings.append(record)

            try:
                analysis = await airca.analyze(logs, correlation_id)
            except Exception as e:
                # If AI fails, we rollback and don't save the analysis
                await db.rollback()
                raise e

            analysis_record = AnalysisResult(
                root_cause=analysis.root_cause,
                impact=analysis.impact,
                fix=analysis.fix,
                correlation_id=correlation_id,
            )
            db.add(analysis_record)

            print("structured_fix before save:", getattr(analysis, "structured_fix", None))
            
            structured_fix_value = getattr(analysis, "structured_fix", None)
            if hasattr(structured_fix_value, "model_dump"):
                structured_fix_value = structured_fix_value.model_dump()
                
            persisted = PersistedAnalysis(
                analysis_id=correlation_id,
                source=logs[0].source if logs else None,
                severity=findings_to_store[0].severity if findings_to_store else analysis.impact or "medium",
                summary=analysis.root_cause or (findings_to_store[0].summary if findings_to_store else None),
                root_cause=analysis.root_cause,
                recommendation=analysis.fix,
                structured_fix=structured_fix_value,
                raw_response_json={
                    "analysis": analysis.model_dump(mode="json") if hasattr(analysis, "model_dump") else analysis,
                    "findings": [f.summary for f in findings_to_store],
                },
                raw_logs=raw_text,
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
                        line_number=getattr(f, "line_number", None),
                    )
                )
            
            await db.commit()
            await db.refresh(persisted)

            # Alerting Integration
            severity = persisted.severity.lower() if persisted.severity else "medium"
            has_critical_failure = any(
                f.severity.lower() in ["high", "critical"] or 
                "Jenkins failure" in f.summary or 
                "CrashLoopBackOff" in f.summary
                for f in findings_to_store
            )

            if severity in ["high", "critical"] or has_critical_failure:
                alert_msg = f"🚨 *Alert: {persisted.severity.upper()} Issue Detected*\n"
                alert_msg += f"Source: {persisted.source}\n"
                alert_msg += f"Summary: {persisted.summary}\n"
                alert_msg += f"Analysis ID: {persisted.analysis_id}"
                
                from app.alerts.slack import send_slack_alert
                from app.alerts.telegram import send_telegram_alert
                from app.alerts.email import send_email_alert
                
                # Send alerts asynchronously
                try:
                    await asyncio.gather(
                        send_slack_alert(alert_msg),
                        send_telegram_alert(alert_msg),
                        send_email_alert(f"DevOps Logs Alert: {persisted.severity}", alert_msg),
                        return_exceptions=True
                    )
                except Exception:
                    pass

            return persisted.analysis_id
        finally:
            await db.close()


@celery.task(bind=True)
def process_upload(self, file_text: str, source: str = "auto"):
    try:
        self.update_state(state="parsing")
        logs = []
        for idx, line in enumerate(file_text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
                if "source" not in obj and source != "auto":
                    obj["source"] = source
                obj.setdefault("metadata", {})["line_number"] = idx
                logs.append(LogEntry(**obj))
            except Exception:
                entry_source = source if source != "auto" else "jenkins"
                logs.append(
                    LogEntry(
                        source=entry_source,
                        service="uploaded",
                        message=stripped,
                        timestamp=datetime.now(timezone.utc),
                        metadata={"line_number": idx},
                    )
                )

        self.update_state(state="running_plugins")
        
        analysis_id = asyncio.run(run_analysis_pipeline(logs, file_text))
        
        self.update_state(state="generating_summary")
        self.update_state(state="completed", meta={"analysis_id": analysis_id})
        return {"analysis_id": analysis_id}
    except Exception as exc:  # noqa: BLE001
        self.update_state(state="failed", meta={"error": str(exc)})
        raise

