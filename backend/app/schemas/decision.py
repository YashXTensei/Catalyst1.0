from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel, Field, field_validator


class DecisionBase(BaseModel):
    decision: str = Field(..., description="Summary of the engineering decision made")
    status: str = Field("accepted", description="Status: accepted, rejected, proposed, deprecated, uncertain")
    context: str = Field(..., description="Context of the discussion")
    rejected_alternatives: List[str] = Field(default_factory=list, description="Alternatives that were considered and rejected")
    reasoning: List[str] = Field(default_factory=list, description="Reasoning and trade-offs that led to the decision")
    affected_components: List[str] = Field(default_factory=list, description="System components affected")
    code_references: List[str] = Field(default_factory=list, description="Code paths or files identified from discussion")
    evidence: List[str] = Field(default_factory=list, description="Exact excerpts supporting this decision")
    source_url: str = Field(..., description="Original GitHub or source URL")

    @field_validator("evidence", "reasoning", "rejected_alternatives", "affected_components", "code_references", mode="before")
    @classmethod
    def ensure_list_of_strings(cls, v: Any) -> List[str]:
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v.strip() else []
        if isinstance(v, (list, tuple, set)):
            return [str(item) for item in v if item]
        return []


class DecisionCreate(DecisionBase):
    repo_id: int
    discussion_id: Optional[int] = None
    source_id: Optional[str] = None
    source_type: str = "github"
    confidence: float = 1.0


class DecisionResponse(DecisionBase):
    id: int
    repo_id: int
    discussion_id: Optional[int] = None
    source_type: str = "github"
    confidence: float = 1.0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DecisionListResponse(BaseModel):
    total: int
    total_pr_decisions: int = 0
    total_issue_decisions: int = 0
    decisions: List[DecisionResponse]
