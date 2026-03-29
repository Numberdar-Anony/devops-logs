from __future__ import annotations
from datetime import timedelta
from typing import List, Optional, Tuple
from uuid import uuid4
from app.models.schemas import LogEntry, FindingCreate


class CorrelationEngine:
    def __init__(self, window_minutes: int = 30):
        self.window = timedelta(minutes=window_minutes)

    def correlate(self, logs: List[LogEntry]) -> Tuple[Optional[str], List[FindingCreate]]:
        if not logs:
            return None, []
        sorted_logs = sorted(logs, key=lambda l: l.timestamp)
        correlation_id: Optional[str] = None
        findings: List[FindingCreate] = []

        for idx, log in enumerate(sorted_logs):
            msg = log.message.lower()
            if log.source == "jenkins" and ("fail" in msg or "exception" in msg):
                jenkins_time = log.timestamp
                terraform_log = self._find_next(sorted_logs, idx, "terraform", jenkins_time)
                k8s_log = None
                if terraform_log:
                    k8s_log = self._find_next(sorted_logs, sorted_logs.index(terraform_log), "kubernetes", terraform_log.timestamp)
                if terraform_log and k8s_log:
                    correlation_id = correlation_id or str(uuid4())
                    chain_details = (
                        f"Jenkins failure at {jenkins_time} -> Terraform error at {terraform_log.timestamp} -> "
                        f"Kubernetes failure at {k8s_log.timestamp}."
                    )
                    findings.append(
                        FindingCreate(
                            plugin_name="correlation_engine",
                            summary="Jenkins -> Terraform -> Kubernetes failure chain detected",
                            details=chain_details,
                            severity="high",
                            source="multi",
                            correlation_id=correlation_id,
                        )
                    )
                    break
        return correlation_id, findings

    def _find_next(self, logs: List[LogEntry], start_idx: int, target_source: str, start_time) -> Optional[LogEntry]:
        for candidate in logs[start_idx + 1 :]:
            if candidate.source != target_source:
                continue
            if candidate.timestamp - start_time <= self.window:
                return candidate
            break
        return None


correlation_engine = CorrelationEngine()
