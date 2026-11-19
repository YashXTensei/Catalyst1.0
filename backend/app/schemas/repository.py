from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RepositoryConnectRequest(BaseModel):
    url: str = Field(..., description="GitHub repository URL (e.g., https://github.com/fastapi/fastapi or owner/repo)")
    discourse_url: Optional[str] = Field(None, description="Optional Discourse forum or topic URL (e.g. https://discuss.python.org/t/topic/123)")


class DiscourseIngestRequest(BaseModel):
    forum_url: str = Field(..., description="Discourse forum base URL or specific topic URL (e.g. https://discuss.python.org/t/pep-572/1234)")
    limit: int = Field(default=5, ge=1, le=30, description="Max topics to ingest")


class RepositoryResponse(BaseModel):
    id: int
    owner: str
    name: str
    full_name: str
    url: str
    description: Optional[str] = None
    stars: int = 0
    default_branch: str = "main"
    indexing_status: str
    indexing_progress: str
    total_discussions: int
    total_decisions: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RepositoryStatusResponse(BaseModel):
    repo_id: int
    full_name: str
    indexing_status: str
    indexing_progress: str
    total_discussions: int
    total_prs: int = 0
    total_issues: int = 0
    total_decisions: int
    status_breakdown: Optional[dict] = None
    source_breakdown: Optional[dict] = None
    recent_decisions: List[dict] = []


class QuickExtractRequest(BaseModel):
    text: str = Field(..., description="Discussion, issue, or PR comment text to extract decisions from")
    title: Optional[str] = Field("Manual Live Ingestion", description="Optional title or context")
    source_url: Optional[str] = Field(None, description="Optional source link")
    author: Optional[str] = Field("collaborator", description="Author handle")

