from sqlalchemy import Column, Integer, String, Text, ARRAY
from app.db.database import Base
from typing import Optional, List
from pydantic import BaseModel
from sqlalchemy import Enum as SAEnum
from app.enums import enums


class NewsEntity(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    media_name = Column(SAEnum(enums.MediaNameEnum), nullable=True)  
    url = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=True)
    origin = Column(SAEnum(enums.OriginEnum), nullable=True)  
    content = Column(Text, nullable=True)
    content_en = Column(Text, nullable=True)
    published_at = Column(Integer, nullable=True)
    authors = Column(ARRAY(String), nullable=True)     # PostgreSQL supports ARRAY
    images = Column(ARRAY(String), nullable=True)