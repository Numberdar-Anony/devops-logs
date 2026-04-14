from __future__ import annotations
import json
import os
from datetime import datetime
from typing import List, Optional, Any, Dict
from openai import AsyncOpenAI
from app.core.config import settings
from app.models.schemas import AnalysisResult, LogEntry, StructuredFix
from app.services.repository_mapper import RepositoryMapper


class AIRootCauseAnalyzer:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or settings.openrouter_api_key
        self.model = model or settings.openrouter_model
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=key,
        ) if key else None

    def _build_prompt(self, logs: List[LogEntry], retry: bool = False) -> str:
        truncated = logs[-20:]
        log_blob = "\n".join(json.dumps(log.model_dump(), default=str) for log in truncated)
        
        json_shape = {
            "summary": "Short summary of the issue",
            "root_cause": "Detailed root cause analysis",
            "recommended_fix_text": "Plain text recommendation",
            "severity": "low|medium|high",
            "affected_resources": ["resource1", "resource2"],
            "timeline": ["event 1", "event 2"],
            "structured_fix": {
                "repository": "repo-name",
                "file": "path/to/file",
                "field": "affected.field",
                "current_value": "old-value",
                "suggested_value": "new-value",
                "reason": "why this change is needed"
            }
        }
        
        prompt = (
            "Analyze these logs and provide a structured root cause analysis.\n"
            f"Return ONLY valid JSON in this exact shape: {json.dumps(json_shape, indent=2)}\n\n"
            f"Logs:\n{log_blob}\n"
        )
        if retry:
            prompt = "CRITICAL: Your previous response was not valid JSON. " + prompt
        return prompt

    async def analyze(self, logs: List[LogEntry], correlation_id: Optional[str] = None) -> AnalysisResult:
        if not logs:
            return AnalysisResult(
                root_cause="No logs provided",
                impact="Unknown",
                fix="Ingest logs first",
                correlation_id=correlation_id,
            )

        if not self.client:
            raise Exception("OpenRouter API key is missing. Set OPENROUTER_API_KEY environment variable.")

        service_name = logs[0].service if logs else None
        source = logs[0].source if logs else None
        log_text = "\n".join([l.message for l in logs[-10:]])
        
        # Get structured remediation from our internal mapper first
        internal_fix = RepositoryMapper.get_structured_remediation(log_text, service_name, source)

        llm_text = ""
        for attempt in range(2):
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert DevOps log analysis assistant. You MUST return valid JSON. No conversational text."
                        },
                        {
                            "role": "user",
                            "content": self._build_prompt(logs, retry=(attempt > 0))
                        }
                    ],
                    response_format={"type": "json_object"}
                )
                llm_text = response.choices[0].message.content
                parsed = json.loads(llm_text)
                break
            except Exception as exc:
                if attempt == 1:
                    # Fallback on second failure
                    parsed = {
                        "summary": "Analysis failed",
                        "root_cause": f"Could not parse LLM response: {str(exc)}",
                        "recommended_fix_text": "Check logs manually",
                        "severity": "medium",
                        "affected_resources": [],
                        "timeline": [],
                        "structured_fix": None
                    }
                continue

        # Merge internal fix with AI response if AI didn't provide one or if internal is better
        ai_structured_fix = parsed.get("structured_fix")
        final_structured_fix = None
        
        if internal_fix:
            # Prefer internal mapper for all fields if they exist as they are exact
            final_structured_fix = StructuredFix(
                repository=internal_fix.get("repository") or (ai_structured_fix.get("repository") if ai_structured_fix else None),
                file=internal_fix.get("file") or (ai_structured_fix.get("file") if ai_structured_fix else None),
                field=internal_fix.get("field") or (ai_structured_fix.get("field") if ai_structured_fix else None),
                current_value=internal_fix.get("current_value") or (ai_structured_fix.get("current_value") if ai_structured_fix else None),
                suggested_value=internal_fix.get("suggested_value") or (ai_structured_fix.get("suggested_value") if ai_structured_fix else None),
                reason=internal_fix.get("reason") or (ai_structured_fix.get("reason") if ai_structured_fix else None)
            )
        elif ai_structured_fix:
            final_structured_fix = StructuredFix(**ai_structured_fix)

        return AnalysisResult(
            root_cause=parsed.get("root_cause", "Unknown"),
            impact=parsed.get("severity", "medium"),
            fix=parsed.get("recommended_fix_text", "No fix provided"),
            correlation_id=correlation_id,
            structured_fix=final_structured_fix
        )


airca = AIRootCauseAnalyzer()
