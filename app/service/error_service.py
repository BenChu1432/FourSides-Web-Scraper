from typing import Dict, List
from app.dto.dto import FetchUrlsResult
from app.models.errorEntity import ErrorEntity, ErrorTypeEnum
from sqlalchemy.ext.asyncio import AsyncSession

async def log_error(
    db: AsyncSession,
    errors: List[Dict]
):
    for error_data in errors:
        error = ErrorEntity(
            failure_type=ErrorTypeEnum(error_data["failure_type"]),
            media_name=error_data.get("media_name"),
            url=str(error_data.get("url")) if error_data.get("url") else None,
            reason=error_data.get("reason"),
        )
        db.add(error)

    await db.commit()