from typing import Dict, List
from app.plugins.base import BasePlugin
from app.models.schemas import LogEntry, FindingCreate


class KubernetesCrashLoopPlugin(BasePlugin):
    name = "kubernetes_crashloop"
    supported_sources = ["kubernetes"]

    async def run(self, logs: List[LogEntry], context: Dict) -> List[FindingCreate]:
        findings: List[FindingCreate] = []
        for log in logs:
            message_lower = log.message.lower()
            reason = str(log.metadata.get("reason", "")).lower()
            if "crashloopbackoff" in message_lower or "crashloopbackoff" in reason:
                container = log.metadata.get("container", log.service or "unknown")
                summary = f"Container {container} is in CrashLoopBackOff"
                details = (
                    f"Detected CrashLoopBackOff for container {container} at {log.timestamp}. "
                    f"Message: {log.message}."
                )
                findings.append(
                    FindingCreate(
                        plugin_name=self.name,
                        summary=summary,
                        details=details,
                        severity="high",
                        source=log.source,
                        correlation_id=context.get("correlation_id"),
                        line_number=log.metadata.get("line_number") if hasattr(log, "metadata") else None,
                    )
                )
        return findings
