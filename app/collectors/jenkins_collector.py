import httpx
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

async def collect_jenkins_logs(job_name: str = "failing-build"):
    if not settings.jenkins_url or not settings.jenkins_user or not settings.jenkins_token:
        logger.warning("Jenkins configuration missing")
        return

    auth = (settings.jenkins_user, settings.jenkins_token)
    url = f"{settings.jenkins_url.rstrip('/')}/job/{job_name}/lastBuild/consoleText"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, auth=auth)
            response.raise_for_status()
            logs_text = response.text

            # Send to ingest
            ingest_url = "http://backend:8000/api/ingest"
            payload = {
                "source": "jenkins",
                "service": job_name,
                "logs": [{"message": line, "level": "INFO"} for line in logs_text.splitlines() if line.strip()]
            }
            resp = await client.post(ingest_url, json=payload)
            resp.raise_for_status()
            logger.info(f"Successfully collected logs from Jenkins job: {job_name}")
    except Exception as e:
        logger.error(f"Failed to collect Jenkins logs: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(collect_jenkins_logs())
