from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class RepositoryConnectRequest(BaseModel):
    url: str = Field(..., description="GitHub repository URL (e.g., https://github.com/fastapi/fastapi or owner/repo)")


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
    total_pages_fetched: int = 0
    total_records_fetched: int = 0
    indexing_next_page: Optional[int] = None
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
    total_pages_fetched: int = 0
    total_records_fetched: int = 0
    indexing_next_page: Optional[int] = None
    recent_decisions: List[dict] = []
