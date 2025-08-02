import os
from typing import Dict, List, Optional
import aiohttp
import asyncio
import logging

from app.enums.enums import ErrorTypeEnum, MediaNameEnum

AWS_LOGGING_LAMBDA_URL = os.getenv("AWS_LOGGING_LAMBDA_URL")

# Optional: Use logging instead of print
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {"detail", "failure_type", "media_name"}

async def send_log_to_lambda(
    jobId: int,
    detail: str,
    failure_type: ErrorTypeEnum,
    media_name: MediaNameEnum,
    urls: Optional[str] = None,
):
    # Validate required fields
    if not detail.strip():
        logger.warning("❌ 'detail' must not be empty.")
        return

    payload = {
        "detail": detail,
        "failure_type": failure_type.value,
        "media_name": media_name.value
    }

    if urls:
        if not isinstance(urls, str):
            logger.warning("❌ 'url' must be a string if provided.")
            return
        payload["url"] = urls

    headers = {"Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(AWS_LOGGING_LAMBDA_URL, json=payload, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("⚠️ Lambda logging failed: %s", error_text)
                else:
                    logger.info("✅ Log successfully sent to Lambda.")
    except Exception as e:
        logger.exception("❌ Exception while sending log to Lambda")