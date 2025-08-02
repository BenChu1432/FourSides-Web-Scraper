from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Boolean,
    ForeignKey,
    Enum as SAEnum,
    ARRAY,
)
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.enums.enums import ErrorTypeEnum, MediaNameEnum
from time import time


class ScrapeJob(Base):
    __tablename__ = "scrape_jobs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    machine_id = Column(String, nullable=False)
    
    start_time = Column(Integer, nullable=False)

    media_name = Column(
        SAEnum(
            MediaNameEnum,
            name="MediaNameEnum",
            create_type=False
        ),
        nullable=False
    )

    end_time = Column(Integer, nullable=True)

    failures = relationship("ScrapeFailure", back_populates="job")


class ScrapeFailure(Base):
    __tablename__ = "scrape_failures"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)

    failure_type = Column(
        SAEnum(
            ErrorTypeEnum,
            name="ErrorTypeEnum",
            create_type=False
        ),
        nullable=False
    )

    media_name = Column(String, nullable=True)
    
    # Representing Prisma's `String[]` using PostgreSQL ARRAY
    url = Column(ARRAY(String), nullable=True)

    detail = Column(Text, nullable=True)

    timestamp = Column(Integer, default=lambda: int(time()))

    resolved = Column(Boolean, default=False)

    jobId = Column(Integer, ForeignKey("scrape_jobs.id"), nullable=True)
    job = relationship("ScrapeJob", back_populates="failures")
