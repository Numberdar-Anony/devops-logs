import re
from typing import Dict, Optional, Any

class RepositoryMapper:
    JENKINS_MAPPING = {
        "zyra-engagement-service": {
            "repo": "gromo-jenkins-dsl",
            "pipeline_file": "pipelines/gromo-heyzyra/zyra-engagement-service/zyra-engagement-service-az.yaml",
            "vertical": "heyzyra-az",
            "team": "heyzyra",
            "values_file": "accounts/heyzyra-az-stg/namespaces/heyzyra/zyra-engagement-service-az/values.yaml"
        },
        "zyra-hi-web": {
            "repo": "gromo-kubernetes-config",
            "values_file": "accounts/heyzyra-az-stg/namespaces/heyzyra/zyra-hi-web-az/values.yaml"
        }
    }

    TERRAFORM_MAPPING = {
        "node group cannot join cluster": {
            "repo": "terraform-infra",
            "directory": "clients/heyzyra/accounts/heyzyra-az-stg/stg/eks",
            "file": "eks_node_group_main.tf",
            "field": "instance_role_arn"
        },
        "subnet does not exist": {
            "repo": "terraform-infra",
            "directory": "clients/heyzyra/accounts/heyzyra-az-stg/stg/common",
            "file": "vpc.tf",
            "field": "subnet_ids"
        }
    }

    K8S_ISSUE_MAPPING = {
        "ImagePullBackOff": {
            "field": "image.tag",
            "recommended_change": "replace image tag with latest successful Jenkins build tag"
        },
        "CrashLoopBackOff": {
            "field": "env",
            "recommended_change": "fix incorrect environment variable or startup config"
        },
        "OOMKilled": {
            "field": "resources.limits.memory",
            "recommended_change": "increase memory limit"
        },
        "IngressUnavailable": {
            "field": "ingress.hosts[0].host",
            "recommended_change": "fix ingress hostname"
        }
    }

    ARGOCD_MAPPINGS = {
        "failing-service degraded": {
            "repository": "gromo-kubernetes-config",
            "file": "apps/failing-service/argocd/application.yaml",
            "field": "spec.syncPolicy",
            "current_value": "prune/selfHeal not enabled",
            "suggested_value": '{"prune": true, "selfHeal": true}',
            "reason": "ArgoCD application is degraded because automatic recovery settings are missing."
        },
        "auth-service missing": {
            "repository": "gromo-kubernetes-config",
            "file": "apps/auth-service/deployment.yaml",
            "field": "namespace",
            "current_value": "missing or incorrect namespace",
            "suggested_value": "auth-production",
            "reason": "ArgoCD cannot locate auth-service because the namespace or manifest path is incorrect."
        },
        "health check failed": {
            "repository": "gromo-kubernetes-config",
            "file": "apps/failing-service/deployment.yaml",
            "field": "livenessProbe.httpGet.path",
            "current_value": "/health",
            "suggested_value": "/v1/health",
            "reason": "The application is degraded because the configured health check path is incorrect."
        }
    }

    @staticmethod
    def get_structured_remediation(log_text: str, service_name: Optional[str] = None, source: Optional[str] = None) -> Optional[Dict[str, Any]]:
        log_text_lower = log_text.lower()
        
        # 0. Handle ArgoCD specific mappings
        if source == "argocd":
            if "failing-service" in log_text_lower and "degraded" in log_text_lower:
                return RepositoryMapper.ARGOCD_MAPPINGS["failing-service degraded"]
            if "auth-service" in log_text_lower and "missing" in log_text_lower:
                return RepositoryMapper.ARGOCD_MAPPINGS["auth-service missing"]
            if "health" in log_text_lower and ("degraded" in log_text_lower or "failed" in log_text_lower):
                return RepositoryMapper.ARGOCD_MAPPINGS["health check failed"]

        # 1. Try to detect K8s issues first as they are common
        for issue, mapping in RepositoryMapper.K8S_ISSUE_MAPPING.items():
            if issue.lower() in log_text_lower:
                res = {
                    "field": mapping["field"],
                    "reason": f"{issue} detected. {mapping['recommended_change']}",
                }
                
                # If we have a service name, try to enrich with repo/file from Jenkins mapping
                if service_name and service_name in RepositoryMapper.JENKINS_MAPPING:
                    service_info = RepositoryMapper.JENKINS_MAPPING[service_name]
                    res.update({
                        "repository": service_info.get("repo"),
                        "file": service_info.get("values_file")
                    })
                return res

        # 2. Try to detect Terraform issues
        for issue, mapping in RepositoryMapper.TERRAFORM_MAPPING.items():
            if issue.lower() in log_text_lower:
                return {
                    "repository": mapping["repo"],
                    "file": f"{mapping['directory']}/{mapping['file']}",
                    "field": mapping["field"],
                    "reason": f"Terraform error '{issue}' detected."
                }

        # 3. Generic service mapping if no specific issue detected but service is known
        if service_name and service_name in RepositoryMapper.JENKINS_MAPPING:
            service_info = RepositoryMapper.JENKINS_MAPPING[service_name]
            return {
                "repository": service_info.get("repo"),
                "file": service_info.get("values_file") or service_info.get("pipeline_file"),
                "reason": f"Generic issue detected for service {service_name}."
            }

        return None
