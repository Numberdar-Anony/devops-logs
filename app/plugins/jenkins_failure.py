from typing import Dict, List
from app.plugins.base import BasePlugin
from app.models.schemas import LogEntry, FindingCreate


class JenkinsFailurePlugin(BasePlugin):
    name = "jenkins_failure"
    supported_sources = ["jenkins"]

    async def run(self, logs: List[LogEntry], context: Dict) -> List[FindingCreate]:
        findings: List[FindingCreate] = []
        for log in logs:
            message_lower = log.message.lower()
            if (
                "finished: failure" in message_lower
                or "build step failed" in message_lower
                or "exception" in message_lower
                or "fail" in message_lower
            ):
                job_name = log.metadata.get("job", log.service or "jenkins-job")
                summary = f"Jenkins job {job_name} failed"
                details = f"Job {job_name} reported failure at {log.timestamp}. Message: {log.message}."
                findings.append(
                    FindingCreate(
                        plugin_name=self.name,
                        summary=summary,
                        details=details,
                        severity="medium",
                        source=log.source,
                        correlation_id=context.get("correlation_id"),
                        line_number=log.metadata.get("line_number") if hasattr(log, "metadata") else None,
                    )
                )
        return findings
