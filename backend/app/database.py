import os
import logging
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import settings

logger = logging.getLogger(__name__)

# Backend directory
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Determine if we are using PostgreSQL or SQLite
db_url = settings.database_url
is_postgres = db_url.startswith("postgresql")

# Ensure SQLite path is always absolute so it points to the exact same file
# regardless of whether the process was started from root or backend/
if "sqlite" in db_url:
    raw_path = db_url.replace("sqlite:///", "").replace("sqlite://", "")
    if not os.path.isabs(raw_path):
        normalized_path = os.path.abspath(os.path.join(backend_dir, raw_path.lstrip("./\\")))
        db_url = f"sqlite:///{normalized_path.replace(os.sep, '/')}"

engine_args = {}
if "sqlite" in db_url:
    engine_args["connect_args"] = {"check_same_thread": False}

try:
    engine = create_engine(db_url, **engine_args)
    # Test connection
    with engine.connect() as conn:
        if is_postgres:
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
                conn.commit()
                logger.info("Successfully verified PostgreSQL connection and pgvector extension.")
            except Exception as e:
                logger.warning(f"Could not enable pgvector extension in PostgreSQL: {e}")
        else:
            logger.info(f"Using SQLite database at {db_url}")
except Exception as e:
    fallback_path = os.path.join(backend_dir, "decisiontrail.db")
    db_url = f"sqlite:///{fallback_path.replace(os.sep, '/')}"
    logger.warning(
        f"Database connection failed: {e}. "
        f"Falling back to local SQLite at {db_url}"
    )
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    is_postgres = False

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def ensure_indexing_schema() -> None:
    """Add incremental-indexing fields to databases created before this release."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "discussions" in tables:
        columns = {column["name"] for column in inspector.get_columns("discussions")}
        if "decision_content_hash" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE discussions ADD COLUMN decision_content_hash VARCHAR(64)"))
            logger.info("Added discussions.decision_content_hash for incremental indexing.")
    if "repositories" in tables:
        columns = {column["name"] for column in inspector.get_columns("repositories")}
        additions = {
            "total_pages_fetched": "INTEGER DEFAULT 0",
            "total_records_fetched": "INTEGER DEFAULT 0",
            "indexing_next_page": "INTEGER",
        }
        for name, definition in additions.items():
            if name not in columns:
                with engine.begin() as connection:
                    connection.execute(text(f"ALTER TABLE repositories ADD COLUMN {name} {definition}"))
                logger.info("Added repositories.%s for indexing progress.", name)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
