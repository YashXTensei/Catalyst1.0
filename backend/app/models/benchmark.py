from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Float
from app.database import Base


class PEPBenchmarkRecord(Base):
    __tablename__ = "pep_benchmark_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pep_number = Column(Integer, unique=True, index=True, nullable=False)
    title = Column(String(512), nullable=False)
    official_url = Column(String(512), nullable=False)
    discussion_url = Column(String(512), nullable=True)
    
    # Execution status: "completed", "unavailable_source", "extraction_failure"
    status = Column(String(50), default="completed", index=True)
    error_message = Column(Text, nullable=True)

    # Counts
    total_ground_truth = Column(Integer, default=0)
    total_recovered = Column(Integer, default=0)
    true_positives = Column(Integer, default=0)
    false_positives = Column(Integer, default=0)
    false_negatives = Column(Integer, default=0)

    # Metrics
    precision = Column(Float, default=0.0)
    recall = Column(Float, default=0.0)
    f1_score = Column(Float, default=0.0)

    # Detailed structured comparisons:
    # [{
    #   "ground_truth_idea": "...",
    #   "ground_truth_reason": "...",
    #   "recovered_idea": "...",
    #   "recovered_reason": "...",
    #   "status": "matched" | "partial" | "missed" | "unmatched_recovery",
    #   "explanation": "...",
    #   "confidence": 0.95,
    #   "evidence_quote": "...",
    #   "discussion_url": "..."
    # }]
    comparisons = Column(JSON, default=list)
    raw_recovered_decisions = Column(JSON, default=list)
    participants = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
