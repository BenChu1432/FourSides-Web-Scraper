from sqlalchemy import Column, Integer, String, Text, ARRAY, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.enums import enums
from app.modals.clusterEntity import ClusterEntity

class NewsEntity(Base):
    __tablename__ = "news"

    id = Column(Integer, primary_key=True, index=True)
    
    media_name = Column(
        SAEnum(
            enums.MediaNameEnum,
            name="news_media_name_enum",   # <-- match this to DB enum type name
            create_type=False
        ),
        nullable=True
    )
    
    url = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=True)
    
    origin = Column(
        SAEnum(
            enums.OriginEnum,
            name="news_origin_enum",       # <-- match this to DB enum type name
            create_type=False
        ),
        nullable=True
    )
    
    content = Column(Text, nullable=True)
    content_en = Column(Text, nullable=True)
    published_at = Column(Integer, nullable=True)
    authors = Column(ARRAY(String), nullable=True)
    images = Column(ARRAY(String), nullable=True)
    
    clusterId = Column(Integer, ForeignKey("cluster.id"), nullable=True)
    cluster = relationship("ClusterEntity", backref="news")