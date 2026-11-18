from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base


class Discussion(Base):
    __tablename__ = "discussions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Unique identifier from the source (e.g. GitHub issue/PR id)
    source_id = Column(String(255), nullable=False, index=True)
    discussion_type = Column(String(50), nullable=False, default="issue")  # issue, pull_request, comment, review, discourse
    number = Column(Integer, nullable=True, index=True)
    title = Column(String(1024), nullable=True)
    body = Column(Text, nullable=True)
    author = Column(String(255), nullable=True)
    url = Column(String(1024), nullable=False)
    state = Column(String(50), default="open")
    
    created_at_source = Column(DateTime, nullable=True)
    indexed_for_decisions = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="discussions")
    decisions = relationship("Decision", back_populates="discussion")
