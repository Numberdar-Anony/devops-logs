from typing import Iterable, List
from app.plugins.base import BasePlugin
from app.plugins.kubernetes_crashloop import KubernetesCrashLoopPlugin
from app.plugins.terraform_error import TerraformErrorPlugin
from app.plugins.jenkins_failure import JenkinsFailurePlugin
from app.models.schemas import LogEntry, FindingCreate


class PluginManager:
    def __init__(self, plugins: Iterable[BasePlugin] | None = None):
        self.plugins: List[BasePlugin] = list(plugins) if plugins else [
            KubernetesCrashLoopPlugin(),
            TerraformErrorPlugin(),
            JenkinsFailurePlugin(),
        ]

    def register(self, plugin: BasePlugin) -> None:
        self.plugins.append(plugin)

    async def run(self, logs: List[LogEntry], context: dict) -> List[FindingCreate]:
        findings: List[FindingCreate] = []
        for plugin in self.plugins:
            relevant_logs = [log for log in logs if log.source in plugin.supported_sources]
            if not relevant_logs:
                continue
            plugin_findings = await plugin.run(relevant_logs, context)
            findings.extend(plugin_findings)
        return findings


plugin_manager = PluginManager()
