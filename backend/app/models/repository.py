from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    owner = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    full_name = Column(String(510), unique=True, nullable=False, index=True)
    url = Column(String(1024), nullable=False)
    description = Column(Text, nullable=True)
    stars = Column(Integer, default=0)
    default_branch = Column(String(100), default="main")

    # Indexing status: "idle", "indexing", "completed", "partial", "failed"
    indexing_status = Column(String(50), default="idle", index=True)
    indexing_progress = Column(String(255), default="Ready to index")
    total_discussions = Column(Integer, default=0)
    total_decisions = Column(Integer, default=0)
    total_pages_fetched = Column(Integer, default=0)
    total_records_fetched = Column(Integer, default=0)
    indexing_next_page = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    discussions = relationship("Discussion", back_populates="repository", cascade="all, delete-orphan")
    decisions = relationship("Decision", back_populates="repository", cascade="all, delete-orphan")
