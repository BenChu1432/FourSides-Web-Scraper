from sqlalchemy import Column, Integer, String, Text, ARRAY
from core.database import Base

class News(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, nullable=True)
    title = Column(String, nullable=True)
    origin = Column(String, nullable=True)
    content = Column(Text, nullable=True)
    published_at = Column(Integer, nullable=True)
    authors = Column(ARRAY(String), nullable=True)     # PostgreSQL supports ARRAY
    images = Column(ARRAY(String), nullable=True)