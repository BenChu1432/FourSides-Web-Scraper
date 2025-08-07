import uuid
from sqlalchemy import UUID, Column, Integer, String, Text, ARRAY, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
from app.db.database import Base
from app.enums import enums
from app.modals.clusterEntity import ClusterEntity

class NewsEntity(Base):
    __tablename__ = "news"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)

    media_name = Column(
        SAEnum(
            enums.MediaNameEnum,
            name="MediaNameEnum",
            create_type=False
        ),
        nullable=True
    )

    url = Column(String, unique=True, nullable=True)
    title = Column(String, nullable=True)

    origin = Column(
        SAEnum(
            enums.OriginEnum,
            name="OriginEnum",
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
    cluster = relationship("ClusterEntity", back_populates="news")
    # Many-to-many through NewsAuthor
    authorships = relationship("NewsAuthorEntity", back_populates="news")