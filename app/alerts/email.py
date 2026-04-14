from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

async def send_email_alert(subject: str, message: str):
    logger.info(f"Email alert triggered: {subject} - {message}")
    # Real implementation would use smtplib or a service like SendGrid
    return True
