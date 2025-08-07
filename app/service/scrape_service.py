import time
from typing import Dict, List, Optional

from sqlalchemy import update
from app.dto.dto import FetchUrlsResult
from app.enums.enums import MediaNameEnum
from app.modals.scrapeEntity import ScrapeFailure, ErrorTypeEnum, ScrapeJob
from sqlalchemy.ext.asyncio import AsyncSession

async def log_scrape_job(
    db: AsyncSession,
    media_name: str,
    machine_id,
) -> int:
    """
    Logs a scrape job with no associated errors.

    Args:
        db (AsyncSession): SQLAlchemy async session.
        machine_id (str): Identifier of the machine running the job.
        media_name (str): Name of the media source (must match MediaNameEnum).

    Returns:
        int: The ID of the created ScrapeJob.
    """
    start_time = int(time.time())
    print("machine_id:",machine_id)
    job = ScrapeJob(
        machine_id=machine_id,
        start_time=start_time,
        media_name=MediaNameEnum(media_name),
    )

    db.add(job)
    await db.flush()  # Ensures job.id is populated before commit
    await db.commit()

    return job.id


async def log_scrape_job_end(
    db: AsyncSession,
    jobId: int,
) -> None:
    """
    Updates the scrape job by setting the end_time to the current Unix timestamp.

    Args:
        db (AsyncSession): SQLAlchemy async session.
        job_id (int): ID of the scrape job to update.
    """
    end_time = int(time.time())

    stmt = (
        update(ScrapeJob)
        .where(ScrapeJob.id == jobId)
        .values(end_time=end_time)
    )
    
    await db.execute(stmt)
    await db.commit()



async def log_scrape_error(
    db: AsyncSession,
    errors: List[Dict],
    job_id: Optional[int] = None,
):
    for error_data in errors:
        # 將 HttpUrl 或其他非 str 類型轉成 str
        urls = error_data.get("url", [])
        urls = [str(url) for url in urls] if isinstance(urls, list) else []

        error = ScrapeFailure(
            failure_type=ErrorTypeEnum(error_data["failure_type"]),
            media_name=error_data.get("media_name"),
            url=urls,
            detail=error_data.get("detail"),
            jobId=job_id
        )
        db.add(error)

    await db.commit()