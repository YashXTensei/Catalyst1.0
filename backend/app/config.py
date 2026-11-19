import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import Field
from dotenv import load_dotenv

# Ensure .env is explicitly loaded from backend directory or root
backend_dir = Path(__file__).resolve().parent.parent
env_path = backend_dir / ".env"
root_env = backend_dir.parent / ".env"

if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
elif root_env.exists():
    load_dotenv(dotenv_path=root_env, override=True)


class Settings(BaseSettings):
    app_name: str = Field(default_factory=lambda: os.getenv("APP_NAME", "DecisionTrail API"))
    app_version: str = Field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    debug: bool = Field(default_factory=lambda: os.getenv("DEBUG", "True").lower() in ("true", "1"))
    port: int = Field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    host: str = Field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))

    # Database: strictly from .env
    database_url: str = Field(
        default_factory=lambda: os.getenv("DATABASE_URL", "sqlite:///./decisiontrail.db")
    )

    # AI / LLM Configuration: strictly from .env
    gemini_api_key: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY")
    )
    gemini_model: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL")
    )
    embedding_model: Optional[str] = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL")
    )

    # GitHub API Configuration: strictly from .env
    github_token: Optional[str] = Field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN")
    )
    indexing_max_pages: int = Field(
        default_factory=lambda: max(1, int(os.getenv("INDEXING_MAX_PAGES", "100")))
    )
    indexing_page_size: int = Field(
        default_factory=lambda: min(100, max(1, int(os.getenv("INDEXING_PAGE_SIZE", "50"))))
    )

    # CORS
    cors_origins: str = Field(
        default_factory=lambda: os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173")
    )

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    class Config:
        env_file = str(env_path) if env_path.exists() else ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
