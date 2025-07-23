from sqlalchemy import Column, Integer, String
from app.db.database import Base


class ClusterEntity(Base):
    __tablename__ = "cluster"

    id = Column(Integer, primary_key=True, index=True)
    cluster_name = Column(String, unique=True, nullable=True)
    cluster_summary = Column(String, unique=True, nullable=True)
    processed_at = Column(Integer, nullable=True)