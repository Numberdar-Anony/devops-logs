import httpx
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_slack_alert(message: str):
    if not settings.slack_webhook_url:
        logger.warning("Slack webhook URL not configured")
        return False
    
    try:
        async with httpx.AsyncClient() as client:
            payload = {"text": message}
            response = await client.post(settings.slack_webhook_url, json=payload)
            response.raise_for_status()
            return True
    except Exception as e:
        logger.error(f"Failed to send Slack alert: {str(e)}")
        return False
