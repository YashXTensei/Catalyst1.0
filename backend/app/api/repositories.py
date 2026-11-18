import logging
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.models.repository import Repository
from app.models.discussion import Discussion
from app.models.decision import Decision
from app.schemas.repository import RepositoryConnectRequest, RepositoryResponse, RepositoryStatusResponse
from app.schemas.decision import DecisionResponse, DecisionListResponse
from app.schemas.qa import QuestionRequest, QuestionResponse
from app.schemas.pr import PRAnalyzeRequest, PRAnalyzeResponse
from app.services.github_service import github_service
from app.services.memory_service import memory_service
from app.agents.decision_extractor import decision_extractor
from app.agents.qa_agent import qa_agent
from app.agents.pr_agent import pr_agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/repositories", tags=["Repositories"])


async def run_background_indexing(repo_id: int, max_pages: int = 2):
    """
    Background worker that fetches historical issues/PRs and extracts decisions incrementally.
    Uses its own db session.
    """
    db: Session = SessionLocal()
    try:
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if not repo:
            return

        repo.indexing_status = "indexing"
        repo.indexing_progress = "Fetching issues and pull requests from GitHub..."
        db.commit()

        total_extracted = 0
        total_fetched = 0

        for page in range(1, max_pages + 1):
            repo.indexing_progress = f"Scanning GitHub discussions (page {page})..."
            db.commit()

            discussions = await github_service.fetch_issues_and_prs(
                owner=repo.owner, repo=repo.name, page=page, per_page=15, state="all"
            )
            if not discussions:
                break

            for disc in discussions:
                total_fetched += 1
                source_id = disc.get("source_id")

                # Store discussion record if new
                existing_disc = db.query(Discussion).filter(
                    Discussion.repo_id == repo.id,
                    Discussion.source_id == source_id
                ).first()

                if not existing_disc:
                    existing_disc = Discussion(
                        repo_id=repo.id,
                        source_id=source_id,
                        discussion_type=disc.get("discussion_type", "issue"),
                        number=disc.get("number"),
                        title=disc.get("title", ""),
                        body=disc.get("body", ""),
                        author=disc.get("author", ""),
                        url=disc.get("url", ""),
                        state=disc.get("state", "open"),
                    )
                    db.add(existing_disc)
                    db.commit()
                    db.refresh(existing_disc)

                # Fetch comments if significant issue/pr
                comments = []
                if disc.get("number"):
                    try:
                        comments = await github_service.fetch_comments(
                            repo.owner, repo.name, disc["number"], limit=5
                        )
                    except Exception:
                        pass

                # Extract decisions
                extracted_decisions = await decision_extractor.extract_from_discussion(
                    title=disc.get("title", ""),
                    body=disc.get("body", ""),
                    source_url=disc.get("url", ""),
                    comments=comments,
                    source_type="github",
                )

                for ed in extracted_decisions:
                    d_saved = await memory_service.store_decision(
                        db=db,
                        repo_id=repo.id,
                        decision_data=ed,
                        discussion_id=existing_disc.id,
                        source_id=f"{source_id}_{ed.get('decision', '')[:20]}"
                    )
                    if d_saved:
                        total_extracted += 1

                # Update live progress
                repo.total_discussions = total_fetched
                repo.total_decisions = db.query(Decision).filter(Decision.repo_id == repo.id).count()
                db.commit()

        repo.indexing_status = "completed"
        repo.indexing_progress = f"Indexing completed. Processed {total_fetched} discussions, extracted {total_extracted} decisions."
        db.commit()
        logger.info(f"Completed indexing repo {repo.full_name}: {total_extracted} decisions extracted.")
    except Exception as e:
        logger.error(f"Error during background indexing for repo {repo_id}: {e}")
        repo = db.query(Repository).filter(Repository.id == repo_id).first()
        if repo:
            repo.indexing_status = "failed"
            repo.indexing_progress = f"Indexing encountered an issue: {str(e)[:150]}"
            db.commit()
    finally:
        db.close()


@router.get("", response_model=List[RepositoryResponse])
def list_repositories(db: Session = Depends(get_db)):
    """List all connected repositories."""
    return db.query(Repository).order_by(Repository.updated_at.desc()).all()


@router.post("/connect", response_model=RepositoryResponse)
async def connect_repository(
    payload: RepositoryConnectRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Validates GitHub URL, fetches repository metadata, registers repo,
    and starts Question-First background indexing.
    """
    try:
        owner, name = github_service.parse_repo_url(payload.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    full_name = f"{owner}/{name}"

    # Check if already connected
    existing = db.query(Repository).filter(Repository.full_name.ilike(full_name)).first()
    if existing:
        # If idle or failed, trigger background indexing refresh
        if existing.indexing_status in ("idle", "failed"):
            background_tasks.add_task(run_background_indexing, existing.id)
        return existing

    # Fetch live metadata from GitHub
    try:
        repo_info = await github_service.get_repository_info(owner, name)
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to GitHub: {str(e)}")

    new_repo = Repository(
        owner=repo_info["owner"],
        name=repo_info["name"],
        full_name=repo_info["full_name"],
        url=repo_info["url"],
        description=repo_info["description"],
        stars=repo_info["stars"],
        default_branch=repo_info["default_branch"],
        indexing_status="indexing",
        indexing_progress="Connecting and initiating memory indexing...",
        total_discussions=0,
        total_decisions=0,
    )
    db.add(new_repo)
    db.commit()
    db.refresh(new_repo)

    # Trigger background indexing
    background_tasks.add_task(run_background_indexing, new_repo.id)

    return new_repo


@router.get("/{repo_id}/status", response_model=RepositoryStatusResponse)
def get_repository_status(repo_id: int, db: Session = Depends(get_db)):
    """Gets real-time indexing status and discussion/decision counters."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    recent_decisions = db.query(Decision).filter(
        Decision.repo_id == repo_id
    ).order_by(Decision.created_at.desc()).limit(5).all()

    return {
        "repo_id": repo.id,
        "full_name": repo.full_name,
        "indexing_status": repo.indexing_status,
        "indexing_progress": repo.indexing_progress,
        "total_discussions": repo.total_discussions,
        "total_decisions": repo.total_decisions,
        "recent_decisions": [
            {
                "id": d.id,
                "decision": d.decision,
                "status": d.status,
                "context": d.context,
                "source_url": d.source_url,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in recent_decisions
        ]
    }


@router.post("/{repo_id}/index")
async def trigger_index(
    repo_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Manually triggers background indexing for a repository."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo.indexing_status = "indexing"
    repo.indexing_progress = "Indexing queued..."
    db.commit()

    background_tasks.add_task(run_background_indexing, repo.id)
    return {"message": "Indexing started in background", "repo_id": repo.id}


@router.get("/{repo_id}/decisions", response_model=DecisionListResponse)
def get_repository_decisions(
    repo_id: int,
    status: Optional[str] = Query(None, description="Filter by status (accepted, rejected, etc.)"),
    search: Optional[str] = Query(None, description="Filter by keyword"),
    db: Session = Depends(get_db)
):
    """Retrieves decisions extracted for this repository with optional filtering."""
    query = db.query(Decision).filter(Decision.repo_id == repo_id)
    if status:
        query = query.filter(Decision.status.ilike(status))
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Decision.decision.ilike(search_filter)) |
            (Decision.context.ilike(search_filter))
        )

    decisions = query.order_by(Decision.created_at.desc()).all()
    return DecisionListResponse(
        total=len(decisions),
        decisions=[DecisionResponse.model_validate(d) for d in decisions]
    )


@router.post("/{repo_id}/ask", response_model=QuestionResponse)
async def ask_project_memory(
    repo_id: int,
    payload: QuestionRequest,
    db: Session = Depends(get_db)
):
    """Answers natural language questions about historical engineering decisions."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return await qa_agent.answer_question(db, repo, payload.question)


@router.post("/{repo_id}/pull-requests/analyze", response_model=PRAnalyzeResponse)
async def analyze_pull_request(
    repo_id: int,
    payload: PRAnalyzeRequest,
    db: Session = Depends(get_db)
):
    """Analyzes a PR for architectural drift and historical decision conflicts."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        return await pr_agent.analyze_pull_request(db, repo, payload.pr_number)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Error analyzing PR #{payload.pr_number}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze PR: {str(e)}")
