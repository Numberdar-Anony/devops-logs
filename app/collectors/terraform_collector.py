import httpx
import logging
import os
from app.core.config import settings

logger = logging.getLogger(__name__)

async def collect_terraform_logs():
    log_path = settings.terraform_log_path
    if not os.path.exists(log_path):
        logger.warning(f"Terraform log path {log_path} not found.")
        return

    try:
        with open(log_path, 'r') as f:
            logs_text = f.read()

        # Send to ingest
        ingest_url = "http://backend:8000/api/ingest"
        payload = {
            "source": "terraform",
            "service": "infrastructure",
            "logs": [{"message": line, "level": "INFO"} for line in logs_text.splitlines() if line.strip()]
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(ingest_url, json=payload, timeout=30.0)
            resp.raise_for_status()
            logger.info(f"Successfully collected logs from Terraform file: {log_path}")
    except Exception as e:
        logger.error(f"Failed to collect Terraform logs: {str(e)}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(collect_terraform_logs())
