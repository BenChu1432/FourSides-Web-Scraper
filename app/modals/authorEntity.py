import uuid
from sqlalchemy import UUID, Column, Integer, String, Text, ARRAY, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.database import Base

class AuthorEntity(Base):
    __tablename__ = "author"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)

    authorships = relationship("NewsAuthorEntity", back_populates="author")
    media_links = relationship("AuthorToNewsMediaEntity", back_populates="author")