from typing import Dict, List
from app.plugins.base import BasePlugin
from app.models.schemas import LogEntry, FindingCreate


class TerraformErrorPlugin(BasePlugin):
    name = "terraform_error"
    supported_sources = ["terraform"]

    async def run(self, logs: List[LogEntry], context: Dict) -> List[FindingCreate]:
        findings: List[FindingCreate] = []
        for log in logs:
            message_lower = log.message.lower()
            if "error:" in message_lower or "failed" in message_lower or "panic" in message_lower:
                summary = "Terraform apply failed"
                resource = log.metadata.get("resource")
                details = f"Terraform reported an error at {log.timestamp}. Message: {log.message}."
                if resource:
                    details += f" Resource: {resource}."
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
