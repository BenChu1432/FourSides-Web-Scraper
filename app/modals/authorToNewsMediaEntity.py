import uuid
from sqlalchemy import UUID, Column, Integer, String, Text, ARRAY, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.database import Base

class AuthorToNewsMediaEntity(Base):
    __tablename__ = "author_to_news_media"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    authorId = Column(UUID(as_uuid=True), ForeignKey("author.id"))
    newsMediaId = Column(UUID(as_uuid=True), ForeignKey("news_media.id"))

    author = relationship("AuthorEntity", back_populates="media_links")
    news_media = relationship("NewsMediaEntity", back_populates="author_links")