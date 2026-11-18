import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import engine, Base
from app.api import health, repositories
import app.models  # ensure models are loaded for Base.metadata.create_all

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("decisiontrail")

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DecisionTrail: AI-powered Engineering Decision Intelligence platform."
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include core routers
app.include_router(health.router)
app.include_router(repositories.router)


@app.on_event("startup")
def on_startup():
    logger.info("Initializing DecisionTrail database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("DecisionTrail API initialized successfully.")


@app.get("/")
def root():
    return {
        "message": "Welcome to DecisionTrail API",
        "docs_url": "/docs",
        "health_url": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)
