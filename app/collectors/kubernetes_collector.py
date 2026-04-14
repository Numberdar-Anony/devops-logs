import httpx
import logging
from kubernetes import client, config
from app.core.config import settings

logger = logging.getLogger(__name__)

async def collect_kubernetes_logs():
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        try:
            config.load_incluster_config()
        except config.config_exception.ConfigException:
            try:
                config.load_kube_config()
            except Exception:
                logger.warning("No Kubernetes config found. Skipping.")
                return

        # Aggressive SSL skip
        configuration = client.Configuration.get_default_copy()
        configuration.verify_ssl = False
        configuration.proxy_verifiy_ssl = False
        configuration.ssl_ca_cert = None
        
        v1 = client.CoreV1Api(client.ApiClient(configuration))
        pods = v1.list_pod_for_all_namespaces(watch=False)
        
        crash_pods = []
        for pod in pods.items:
            # Check for CrashLoopBackOff
            for container_status in (pod.status.container_statuses or []):
                if container_status.state.waiting and container_status.state.waiting.reason == 'CrashLoopBackOff':
                    crash_pods.append(pod)
                    break
        
        for pod in crash_pods:
            try:
                # Fetch last 100 lines of logs
                logs = v1.read_namespaced_pod_log(name=pod.metadata.name, namespace=pod.metadata.namespace, tail_lines=100)
                
                # Send to ingest
                ingest_url = "http://backend:8000/api/ingest"
                payload = {
                    "source": "kubernetes",
                    "service": f"{pod.metadata.namespace}/{pod.metadata.name}",
                    "logs": [{"message": line, "level": "ERROR"} for line in logs.splitlines() if line.strip()]
                }
                async with httpx.AsyncClient() as http_client:
                    resp = await http_client.post(ingest_url, json=payload)
                    resp.raise_for_status()
                    logger.info(f"Successfully collected logs from Kubernetes pod: {pod.metadata.name}")
            except Exception as e:
                logger.error(f"Failed to get logs for pod {pod.metadata.name}: {str(e)}")

    except Exception as e:
        logger.error(f"Failed to collect Kubernetes logs: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(collect_kubernetes_logs())
