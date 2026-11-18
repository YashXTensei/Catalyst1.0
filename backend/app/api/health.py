import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db, is_postgres
from app.config import settings

router = APIRouter(tags=["Health"])


@router.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db_status = "error"
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"

    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "database": {
            "status": db_status,
            "engine": "postgresql" if is_postgres else "sqlite",
        },
        "services": {
            "gemini_configured": bool(settings.gemini_api_key or os.getenv("GEMINI_API_KEY")),
            "github_token_configured": bool(settings.github_token or os.getenv("GITHUB_TOKEN")),
        }
    }
