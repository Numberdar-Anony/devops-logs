import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def collect_argocd_logs():
    if not settings.argocd_url or not settings.argocd_token:
        logger.warning("ArgoCD configuration missing")
        return

    url = f"{settings.argocd_url.rstrip('/')}/api/v1/applications"
    headers = {"Authorization": f"Bearer {settings.argocd_token}"}

    try:
        async with httpx.AsyncClient(verify=False) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            apps = response.json().get('items', [])

            sync_failures = []
            for app in apps:
                status = app.get('status', {})
                sync_status = status.get('sync', {}).get('status')
                health_status = status.get('health', {}).get('status')
                
                if sync_status == 'OutOfSync' or health_status == 'Degraded':
                    sync_failures.append({
                        "app_name": app['metadata']['name'],
                        "sync_status": sync_status,
                        "health_status": health_status,
                        "conditions": status.get('conditions', [])
                    })

            if sync_failures:
                # Send to ingest
                ingest_url = "http://backend:8000/api/ingest"
                payload = {
                    "source": "argocd",
                    "service": "applications",
                    "logs": [{"message": f"App {f['app_name']} is {f['sync_status']} and {f['health_status']}", "level": "ERROR"} for f in sync_failures]
                }
                resp = await client.post(ingest_url, json=payload, timeout=30.0)
                resp.raise_for_status()
                logger.info(f"Successfully collected {len(sync_failures)} sync failures from ArgoCD")
    except Exception as e:
        logger.error(f"Failed to collect ArgoCD logs: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(collect_argocd_logs())
