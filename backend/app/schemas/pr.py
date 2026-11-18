from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.decision import DecisionResponse


class PRAnalyzeRequest(BaseModel):
    pr_number: int = Field(..., ge=1, description="Pull Request number to analyze")


class PotentialConflict(BaseModel):
    decision_id: int
    decision_title: str
    status: str
    conflict_risk: str  # "high", "medium", "low", "none"
    explanation: str
    affected_files: List[str] = []
    evidence_snippet: str
    recommendation: str
    source_url: str


class PRAnalyzeResponse(BaseModel):
    pr_number: int
    pr_title: str
    pr_url: str
    author: Optional[str] = None
    state: str
    changed_files: List[str] = []
    summary: str
    related_decisions: List[DecisionResponse] = []
    potential_conflicts: List[PotentialConflict] = []
    overall_risk: str  # "high", "medium", "low", "none"
    recommendations: List[str] = []
