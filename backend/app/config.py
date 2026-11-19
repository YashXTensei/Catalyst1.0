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
    # Dedicated Subsystem Keys (Optional: fall back to gemini_api_key if unset or empty)
    gemini_api_key_extraction: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY_EXTRACTION")
    )
    gemini_api_key_embedding: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY_EMBEDDING")
    )
    gemini_api_key_qa: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY_QA")
    )
    gemini_api_key_pr: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_API_KEY_PR")
    )
    gemini_model: Optional[str] = Field(
        default_factory=lambda: os.getenv("GEMINI_MODEL")
    )
    embedding_model: Optional[str] = Field(
        default_factory=lambda: os.getenv("EMBEDDING_MODEL")
    )

    def get_gemini_key_for(self, subsystem: str = "default") -> Optional[str]:
        """
        Returns the subsystem-dedicated Gemini API key if configured and non-empty;
        otherwise falls back to the primary gemini_api_key.
        """
        sub = (subsystem or "default").lower().strip()
        key = None
        if sub in ("extraction", "extract", "extractor"):
            key = self.gemini_api_key_extraction or os.getenv("GEMINI_API_KEY_EXTRACTION")
        elif sub in ("embedding", "embed", "embeddings"):
            key = self.gemini_api_key_embedding or os.getenv("GEMINI_API_KEY_EMBEDDING")
        elif sub in ("qa", "chat", "question"):
            key = self.gemini_api_key_qa or os.getenv("GEMINI_API_KEY_QA")
        elif sub in ("pr", "sentinel", "drift"):
            key = self.gemini_api_key_pr or os.getenv("GEMINI_API_KEY_PR")

        if key and key.strip():
            return key.strip()

        fallback = self.gemini_api_key or os.getenv("GEMINI_API_KEY")
        return fallback.strip() if fallback else None

    # GitHub API Configuration: strictly from .env
    github_token: Optional[str] = Field(
        default_factory=lambda: os.getenv("GITHUB_TOKEN")
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
