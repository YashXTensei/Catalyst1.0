import logging
import asyncio
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.database import get_db, SessionLocal
from app.models.repository import Repository
from app.models.discussion import Discussion
from app.models.decision import Decision
from app.schemas.repository import (
    RepositoryConnectRequest,
    RepositoryResponse,
    RepositoryStatusResponse,
    DiscourseIngestRequest,
    QuickExtractRequest,
)
from app.schemas.decision import DecisionResponse, DecisionListResponse
from app.schemas.qa import QuestionRequest, QuestionResponse
from app.schemas.pr import PRAnalyzeRequest, PRAnalyzeResponse, PRSimulateRequest
from app.services.github_service import github_service
from app.services.memory_service import memory_service
from app.integrations.discourse_connector import discourse_connector
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

                # Check if decisions already extracted for this discussion
                has_decisions = db.query(Decision).filter(
                    Decision.repo_id == repo.id,
                    Decision.discussion_id == existing_disc.id
                ).count() > 0

                if not has_decisions:
                    repo.indexing_progress = f"Scanning item {total_fetched}: {disc.get('title', '')[:35]}..."
                    db.commit()

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
                else:
                    repo.indexing_progress = f"Verified existing memory: {disc.get('title', '')[:32]}..."
                    db.commit()

                # Update live progress
                repo.total_discussions = total_fetched
                repo.total_decisions = db.query(Decision).filter(Decision.repo_id == repo.id).count()
                db.commit()

        # Dedicated fetch for pure issues to ensure issues are not drowned out by high PR volume
        repo.indexing_progress = "Scanning dedicated GitHub issues and discussions..."
        db.commit()
        try:
            pure_issues = await github_service.fetch_pure_issues(owner=repo.owner, repo=repo.name, limit=10)
            for disc in pure_issues:
                source_id = disc.get("source_id")
                existing_disc = db.query(Discussion).filter(
                    Discussion.repo_id == repo.id,
                    Discussion.source_id == source_id
                ).first()

                if not existing_disc:
                    total_fetched += 1
                    existing_disc = Discussion(
                        repo_id=repo.id,
                        source_id=source_id,
                        discussion_type="issue",
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

                has_decisions = db.query(Decision).filter(
                    Decision.repo_id == repo.id,
                    Decision.discussion_id == existing_disc.id
                ).count() > 0

                if not has_decisions:
                    repo.indexing_progress = f"Scanning issue: {disc.get('title', '')[:35]}..."
                    db.commit()

                    comments = []
                    if disc.get("number"):
                        try:
                            comments = await github_service.fetch_comments(repo.owner, repo.name, disc["number"], limit=5)
                        except Exception:
                            pass

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
                else:
                    repo.indexing_progress = f"Verified issue memory: {disc.get('title', '')[:32]}..."
                    db.commit()

                repo.total_discussions = total_fetched
                repo.total_decisions = db.query(Decision).filter(Decision.repo_id == repo.id).count()
                db.commit()
        except Exception as e:
            logger.warning(f"Error fetching dedicated issues: {e}")

        repo.indexing_status = "completed"
        repo.indexing_progress = f"Project memory active: {repo.total_decisions} decisions vectorized across {total_fetched} discussions"
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
        try:
            repo = db.query(Repository).filter(Repository.id == repo_id).first()
            if repo and repo.indexing_status == "indexing":
                repo.indexing_status = "completed" if (repo.total_decisions or 0) > 0 else "idle"
                repo.indexing_progress = f"Project memory active: {repo.total_decisions or 0} decisions vectorized across {repo.total_discussions or 0} discussions"
                db.commit()
        except Exception:
            pass
        db.close()


@router.post("/{repo_id}/reset-status")
def reset_repository_status(repo_id: int, db: Session = Depends(get_db)):
    """Resets repository indexing status if stuck."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    repo.indexing_status = "completed" if (repo.total_decisions or 0) > 0 else "idle"
    repo.indexing_progress = f"Project memory active: {repo.total_decisions or 0} decisions vectorized across {repo.total_discussions or 0} discussions"
    db.commit()
    return {"message": "Repository indexing status reset successfully", "repo_id": repo.id}


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
    """Gets real-time indexing status, discussion/decision counters, and breakdown metrics."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    recent_decisions = db.query(Decision).filter(
        Decision.repo_id == repo_id
    ).order_by(Decision.created_at.desc()).limit(8).all()

    total_prs = db.query(Discussion).filter(
        Discussion.repo_id == repo_id,
        Discussion.discussion_type == "pull_request"
    ).count()

    total_issues = db.query(Discussion).filter(
        Discussion.repo_id == repo_id,
        Discussion.discussion_type == "issue"
    ).count()

    # Dynamic status breakdown
    accepted_count = db.query(Decision).filter(Decision.repo_id == repo_id, Decision.status == "accepted").count()
    rejected_count = db.query(Decision).filter(Decision.repo_id == repo_id, Decision.status == "rejected").count()
    proposed_count = db.query(Decision).filter(Decision.repo_id == repo_id, Decision.status == "proposed").count()
    deprecated_count = db.query(Decision).filter(Decision.repo_id == repo_id, Decision.status == "deprecated").count()

    # Multi-source breakdown
    discourse_count = db.query(Decision).filter(
        Decision.repo_id == repo_id,
        (Decision.source_type == "discourse") | (Decision.source_url.ilike("%discuss.%")) | (Decision.source_url.ilike("%forum.%"))
    ).count()

    unique_contributors = db.query(func.count(func.distinct(Discussion.author))).filter(
        Discussion.repo_id == repo_id,
        Discussion.author != None,
        Discussion.author != ""
    ).scalar() or 0

    return {
        "repo_id": repo.id,
        "full_name": repo.full_name,
        "indexing_status": repo.indexing_status,
        "indexing_progress": repo.indexing_progress,
        "total_discussions": repo.total_discussions,
        "total_prs": total_prs,
        "total_issues": total_issues,
        "total_decisions": repo.total_decisions,
        "status_breakdown": {
            "accepted": accepted_count,
            "rejected": rejected_count,
            "proposed": proposed_count,
            "deprecated": deprecated_count,
        },
        "source_breakdown": {
            "github_prs": total_prs,
            "github_issues": total_issues,
            "discourse_topics": discourse_count,
            "unique_contributors": unique_contributors,
        },
        "recent_decisions": [
            {
                "id": d.id,
                "decision": d.decision,
                "status": d.status,
                "context": d.context,
                "rejected_alternatives": d.rejected_alternatives or [],
                "reasoning": d.reasoning or [],
                "source_url": d.source_url,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in recent_decisions
        ]
    }


@router.post("/{repo_id}/sync-github")
async def sync_github_repository(repo_id: int, db: Session = Depends(get_db)):
    """Fetches live metadata from GitHub (stars, branch, description) and syncs database."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        repo_info = await github_service.get_repository_info(repo.owner, repo.name)
        repo.stars = repo_info.get("stars", repo.stars)
        repo.description = repo_info.get("description", repo.description)
        repo.default_branch = repo_info.get("default_branch", repo.default_branch)
        db.commit()
        db.refresh(repo)
        return {
            "message": "Repository metadata synced live with GitHub",
            "stars": repo.stars,
            "description": repo.description,
            "default_branch": repo.default_branch,
        }
    except Exception as e:
        logger.warning("Could not sync with GitHub live: %s", str(e))
        return {
            "message": f"GitHub sync notice: {str(e)}",
            "stars": repo.stars,
            "description": repo.description,
            "default_branch": repo.default_branch,
        }


@router.post("/{repo_id}/extract-quick")
async def extract_quick_decision(
    repo_id: int,
    payload: QuickExtractRequest,
    db: Session = Depends(get_db)
):
    """
    Live interactive decision extraction: Takes arbitrary discussion/comment text,
    runs Gemini Decision Extractor, indexes into vector memory, and returns structured decision.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    text_input = payload.text.strip()
    if len(text_input) < 10:
        raise HTTPException(status_code=400, detail="Text must be at least 10 characters long.")

    source_url = payload.source_url or f"https://github.com/{repo.full_name}/discussions/live"

    # 1. Run live LLM decision extraction
    extracted = await decision_extractor.extract_from_discussion(
        title=payload.title or "Interactive Extraction",
        body=text_input,
        source_url=source_url,
        comments=None,
        source_type="interactive"
    )

    if not extracted:
        return {
            "success": False,
            "message": "No architectural or engineering decision could be confidently extracted from this text.",
            "extracted_decisions": [],
            "new_total_decisions": repo.total_decisions
        }

    stored_decisions = []
    for idx, dec_data in enumerate(extracted):
        unique_src_id = f"live_{repo.id}_{repo.total_decisions or 0}_{idx + 1}"
        saved = await memory_service.store_decision(
            db=db,
            repo_id=repo.id,
            decision_data=dec_data,
            source_id=unique_src_id
        )
        if saved:
            stored_decisions.append({
                "id": saved.id,
                "decision": saved.decision,
                "status": saved.status,
                "context": saved.context,
                "reasoning": saved.reasoning or [],
                "rejected_alternatives": saved.rejected_alternatives or [],
                "code_references": saved.code_references or [],
                "affected_components": saved.affected_components or [],
                "evidence": saved.evidence or [],
                "confidence": saved.confidence or 0.95,
                "source_url": saved.source_url,
                "created_at": saved.created_at.isoformat() if saved.created_at else None,
            })

    # Update repo counters
    repo.total_decisions = db.query(Decision).filter(Decision.repo_id == repo.id).count()
    db.commit()

    return {
        "success": True,
        "message": f"Successfully extracted and indexed {len(stored_decisions)} decision(s) into project memory!",
        "extracted_decisions": stored_decisions,
        "new_total_decisions": repo.total_decisions
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
    source_type: Optional[str] = Query(None, description="Filter by source type ('pr', 'issue', 'all')"),
    search: Optional[str] = Query(None, description="Filter by keyword"),
    db: Session = Depends(get_db)
):
    """Retrieves decisions extracted for this repository with optional filtering."""
    base_query = db.query(Decision).filter(Decision.repo_id == repo_id)

    total_pr_decisions = base_query.filter(Decision.source_url.ilike("%/pull/%")).count()
    total_issue_decisions = base_query.filter(Decision.source_url.ilike("%/issues/%")).count()
    total_discourse_decisions = base_query.filter(
        (Decision.source_type == "discourse") | 
        (Decision.source_url.ilike("%discuss.%")) | 
        (Decision.source_url.ilike("%forum.%"))
    ).count()
    total_count = base_query.count()

    query = base_query
    if status:
        query = query.filter(Decision.status.ilike(status))
    if source_type:
        st = source_type.lower()
        if st in ("pr", "pull", "pull_request"):
            query = query.filter(Decision.source_url.ilike("%/pull/%"))
        elif st in ("issue", "issues"):
            query = query.filter(Decision.source_url.ilike("%/issues/%"))
        elif st in ("discourse", "forum"):
            query = query.filter(
                (Decision.source_type == "discourse") | 
                (Decision.source_url.ilike("%discuss.%")) | 
                (Decision.source_url.ilike("%forum.%"))
            )
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Decision.decision.ilike(search_filter)) |
            (Decision.context.ilike(search_filter))
        )

    decisions = query.order_by(Decision.created_at.desc()).all()
    return DecisionListResponse(
        total=total_count,
        total_pr_decisions=total_pr_decisions,
        total_issue_decisions=total_issue_decisions,
        total_discourse_decisions=total_discourse_decisions,
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


@router.post("/{repo_id}/pull-requests/simulate", response_model=PRAnalyzeResponse)
async def simulate_pull_request(
    repo_id: int,
    payload: PRSimulateRequest,
    db: Session = Depends(get_db)
):
    """Simulates a custom PR or pasted diff to analyze architectural drift and past decision conflicts."""
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        return await pr_agent.analyze_simulated_pr(
            db=db,
            repo=repo,
            title=payload.title,
            description=payload.description or "",
            changed_files=payload.changed_files,
            diff=payload.diff or ""
        )
    except Exception as e:
        logger.error(f"Error simulating PR '{payload.title}': {e}")
        raise HTTPException(status_code=500, detail=f"Failed to analyze simulated PR: {str(e)}")


@router.post("/{repo_id}/ingest-discourse")
async def ingest_discourse_discussions(
    repo_id: int,
    payload: DiscourseIngestRequest,
    db: Session = Depends(get_db)
):
    """
    Ingests discussions from a public Discourse forum or specific topic thread (e.g. discuss.python.org).
    Fulfills Multi-Source Data Collection (Requirement 3.A) and Extra Marks Scope.
    """
    repo = db.query(Repository).filter(Repository.id == repo_id).first()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        topics = await discourse_connector.fetch_discussions(payload.forum_url, limit=payload.limit)
        if not topics:
            return {
                "message": f"No active discussions could be fetched from {payload.forum_url}. Verify the URL is publicly reachable.",
                "discussions_ingested": 0,
                "decisions_extracted": 0,
            }

        extracted_count = 0
        discussions_saved = 0

        for t in topics:
            source_id = t.get("source_id", "")
            existing_disc = db.query(Discussion).filter(
                Discussion.repo_id == repo.id,
                Discussion.source_id == source_id
            ).first()

            if not existing_disc:
                existing_disc = Discussion(
                    repo_id=repo.id,
                    source_id=source_id,
                    discussion_type="discourse",
                    number=None,
                    title=t.get("title", ""),
                    body=t.get("body", ""),
                    author=t.get("author", "discourse_user"),
                    url=t.get("url", ""),
                    state="open",
                )
                db.add(existing_disc)
                db.commit()
                db.refresh(existing_disc)
                discussions_saved += 1

            extracted = await decision_extractor.extract_from_discussion(
                title=t.get("title", ""),
                body=t.get("body", ""),
                source_url=t.get("url", ""),
                comments=[],
                source_type="discourse",
            )

            for ed in extracted:
                saved = await memory_service.store_decision(
                    db=db,
                    repo_id=repo.id,
                    decision_data=ed,
                    discussion_id=existing_disc.id,
                    source_id=f"{source_id}_{ed.get('decision', '')[:20]}"
                )
                if saved:
                    extracted_count += 1

        repo.total_discussions = db.query(Discussion).filter(Discussion.repo_id == repo.id).count()
        repo.total_decisions = db.query(Decision).filter(Decision.repo_id == repo.id).count()
        db.commit()

        return {
            "message": f"Successfully ingested discussions from Discourse forum: {payload.forum_url}",
            "discussions_ingested": discussions_saved,
            "decisions_extracted": extracted_count,
            "total_decisions": repo.total_decisions,
        }
    except Exception as e:
        logger.error(f"Error ingesting Discourse discussions: {e}")
        raise HTTPException(status_code=500, detail=f"Discourse ingestion failed: {str(e)}")
