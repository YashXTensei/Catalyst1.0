from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship
from app.database import Base


class Decision(Base):
    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False, index=True)
    discussion_id = Column(Integer, ForeignKey("discussions.id", ondelete="SET NULL"), nullable=True)

    # Core decision fields specified in architecture
    decision = Column(String(512), nullable=False, index=True)
    status = Column(String(50), default="accepted", index=True)  # accepted, rejected, proposed, deprecated, uncertain
    context = Column(Text, nullable=False)
    rejected_alternatives = Column(JSON, default=list)
    reasoning = Column(JSON, default=list)
    affected_components = Column(JSON, default=list)
    code_references = Column(JSON, default=list)
    evidence = Column(JSON, default=list)
    
    source_url = Column(String(1024), nullable=False)
    source_type = Column(String(50), default="github")
    source_id = Column(String(255), nullable=True, index=True)
    confidence = Column(Float, default=1.0)
    
    # Store embedding as JSON vector (dynamically sized based on EMBEDDING_MODEL from .env)
    embedding = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    repository = relationship("Repository", back_populates="decisions")
    discussion = relationship("Discussion", back_populates="decisions")
