from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.decision import DecisionResponse


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=2, description="Natural language question about engineering decisions")


class Citation(BaseModel):
    decision_id: int
    decision_title: str
    source_url: str
    evidence_snippet: str
    source_type: str = "github"


class QuestionResponse(BaseModel):
    question: str
    answer: str
    confidence: str = "high"  # high, medium, low, insufficient_evidence
    evidence_found: bool = True
    decisions_used: List[DecisionResponse] = []
    citations: List[Citation] = []
    search_strategy: str = "hybrid"  # cached_memory, targeted_search, or combination
