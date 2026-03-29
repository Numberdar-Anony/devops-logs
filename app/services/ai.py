from __future__ import annotations
import json
from datetime import datetime
from typing import List, Optional
import httpx
from app.core.config import settings
from app.models.schemas import AnalysisResult, LogEntry


class AIRootCauseAnalyzer:
    def __init__(self, base_url: str | None = None, model: str | None = None):
        base = base_url or settings.ollama_base_url
        self.url = f"{base.rstrip('/')}/api/generate"
        self.model = model or settings.ollama_model

    def _build_prompt(self, logs: List[LogEntry]) -> str:
        truncated = logs[-20:]
        log_blob = "\n".join(json.dumps(log.model_dump(), default=str) for log in truncated)
        prompt = (
            "Analyze these logs and explain root cause and fix. "
            "Return JSON with keys root_cause, impact, fix.\n\n"
            f"Logs:\n{log_blob}\n"
        )
        return prompt

    async def analyze(self, logs: List[LogEntry], correlation_id: Optional[str] = None) -> AnalysisResult:
        if not logs:
            return AnalysisResult(
                root_cause="No logs provided",
                impact="Unknown",
                fix="Ingest logs first",
                correlation_id=correlation_id,
            )
        payload = {"model": self.model, "prompt": self._build_prompt(logs), "stream": False}
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.url, json=payload)
                response.raise_for_status()
                body = response.json()
                llm_text = body.get("response", "")
        except Exception as exc:  # noqa: BLE001
            return AnalysisResult(
                root_cause=f"LLM call failed: {repr(exc)}",
                impact="Unknown",
                fix="Check Ollama configuration",
                correlation_id=correlation_id,
                created_at=datetime.utcnow(),
            )

        try:
            parsed = json.loads(llm_text)
            root_cause = parsed.get("root_cause") or llm_text
            impact = parsed.get("impact") or "Not provided"
            fix = parsed.get("fix") or "Not provided"
        except json.JSONDecodeError:
            root_cause = llm_text
            impact = "Not parsed"
            fix = "Not parsed"

        return AnalysisResult(root_cause=root_cause, impact=impact, fix=fix, correlation_id=correlation_id)


airca = AIRootCauseAnalyzer()
