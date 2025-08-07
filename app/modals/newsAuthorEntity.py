import uuid
from sqlalchemy import UUID, Column, Integer, String, Text, ARRAY, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.database import Base

class NewsAuthorEntity(Base):
    __tablename__ = "news_author"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    newsId = Column(UUID(as_uuid=True), ForeignKey("news.id"))
    authorId = Column(UUID(as_uuid=True), ForeignKey("author.id"))

    news = relationship("NewsEntity", back_populates="authorships")
    author = relationship("AuthorEntity", back_populates="authorships")

