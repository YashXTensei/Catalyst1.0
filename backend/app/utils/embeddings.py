import os
import math
import logging
import hashlib
from typing import List
import numpy as np
from app.config import settings

logger = logging.getLogger(__name__)

# Cache client instance
_gemini_client = None


def get_gemini_client():
    global _gemini_client
    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if _gemini_client is None and api_key:
        try:
            from google import genai
            _gemini_client = genai.Client(api_key=api_key)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini GenAI client: {e}")
            _gemini_client = None
    return _gemini_client


def get_fallback_embedding(text: str, dim: int = 768) -> List[float]:
    """
    Deterministic pseudo-semantic vector generator for fallback when API keys are absent.
    Uses rolling hash and character n-grams normalized to unit length.
    """
    vec = np.zeros(dim, dtype=np.float32)
    words = text.lower().split()
    for i, word in enumerate(words):
        h = int(hashlib.sha256(word.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        vec[idx] += 1.0 / (1.0 + math.log(i + 1))

    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


async def generate_embedding(text: str) -> List[float]:
    """
    Generates embedding for text using EMBEDDING_MODEL from .env.
    Falls back gracefully to deterministic vectorizer if not configured.
    """
    if not text or not text.strip():
        return [0.0] * 768

    client = get_gemini_client()
    if client and settings.embedding_model:
        try:
            # Using official google-genai SDK with model from .env
            response = client.models.embed_content(
                model=settings.embedding_model,
                contents=text[:8000]
            )
            if hasattr(response, "embedding") and response.embedding:
                return response.embedding.values
            elif hasattr(response, "embeddings") and response.embeddings:
                return response.embeddings[0].values
        except Exception as e:
            logger.warning(f"Gemini embedding API call failed ({settings.embedding_model}): {e}. Using deterministic vectorizer.")

    return get_fallback_embedding(text)


def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    """Computes cosine similarity between two float vectors."""
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    a = np.array(v1, dtype=np.float32)
    b = np.array(v2, dtype=np.float32)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))
