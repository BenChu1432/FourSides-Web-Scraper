from sqlalchemy import Column, Integer, String, Text, Boolean, Enum as SAEnum, TIMESTAMP
from app.db.database import Base
from datetime import datetime
from app.enums.enums import ErrorTypeEnum
from time import time


class ErrorEntity(Base):
    __tablename__ = "scrape_failures"

    id = Column(Integer, primary_key=True, index=True,autoincrement=True)
    failure_type = Column(SAEnum(ErrorTypeEnum), nullable=False)
    media_name = Column(String, nullable=True)
    url = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)   # e.g., "403 Forbidden", "timeout"
    timestamp = Column(Integer, default=lambda: int(time()))
    resolved  = Column(Boolean, default=False)