import uuid
from sqlalchemy import UUID, Column, Integer, String, Text, ARRAY, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.database import Base

class NewsMediaEntity(Base):
    __tablename__ = "news_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    imageUrl = Column(String, nullable=False)

    author_links = relationship("AuthorToNewsMediaEntity", back_populates="news_media")
