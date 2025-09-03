import uuid
from sqlalchemy import UUID, Column, String, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base

class NewsQuestionEntity(Base):
    __tablename__ = "news_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    question = Column(Text, nullable=False)
    options = Column(JSONB, nullable=False)       
    answer = Column(String, nullable=False)       
    explanation = Column(Text, nullable=True)

    newsId = Column(UUID(as_uuid=True), ForeignKey("news.id"), nullable=False)
    news = relationship("NewsEntity", back_populates="questions")