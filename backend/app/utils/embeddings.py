import os
import math
import logging
import hashlib
from typing import List, Optional, Sequence
import numpy as np
from app.config import settings

logger = logging.getLogger(__name__)

# `gemini-embedding-001` produces 3072-dimensional vectors unless the caller
# explicitly requests output dimensionality. DecisionTrail does not request a
# reduced dimensionality, so this is the only dimension accepted for persisted
# production embeddings.
EMBEDDING_DIMENSION = 3072

# Cache client instances keyed by API key
_gemini_clients: dict = {}


def get_gemini_client(subsystem: str = "default", api_key: Optional[str] = None):
    """
    Returns an initialized GenAI client for the specified subsystem or API key.
    Subsystem-specific keys fall back to GEMINI_API_KEY when unset.
    """
    global _gemini_clients
    target_key = api_key or settings.get_gemini_key_for(subsystem)
    if not target_key:
        return None

    if target_key not in _gemini_clients:
        try:
            from google import genai
            _gemini_clients[target_key] = genai.Client(api_key=target_key)
            logger.info(f"Initialized Gemini GenAI client for subsystem '{subsystem}'.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini GenAI client for subsystem '{subsystem}': {e}")
            return None
    return _gemini_clients.get(target_key)


def get_fallback_embedding(text: str, dim: int = EMBEDDING_DIMENSION) -> List[float]:
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


def is_valid_embedding(
    embedding: Optional[Sequence[float]],
    expected_dimension: int = EMBEDDING_DIMENSION,
) -> bool:
    """Return whether an embedding is safe to persist and search."""
    if not embedding or len(embedding) != expected_dimension:
        return False

    try:
        values = np.asarray(embedding, dtype=np.float32)
    except (TypeError, ValueError):
        return False

    return bool(np.isfinite(values).all() and np.linalg.norm(values) > 0)


async def generate_embedding(text: str, subsystem: str = "embedding") -> Optional[List[float]]:
    """
    Generates embedding for text using EMBEDDING_MODEL from .env.
    Uses the dedicated embedding Gemini API key (or primary fallback).
    Returns ``None`` when Gemini cannot produce a valid embedding. This avoids
    silently mixing fallback vectors with vectors from the configured model.
    """
    if not text or not text.strip():
        return None

    client = get_gemini_client(subsystem=subsystem)
    if client and settings.embedding_model:
        try:
            # Using official google-genai SDK with model from .env
            response = client.models.embed_content(
                model=settings.embedding_model,
                contents=text[:8000]
            )
            embedding = None
            if hasattr(response, "embedding") and response.embedding:
                embedding = response.embedding.values
            elif hasattr(response, "embeddings") and response.embeddings:
                embedding = response.embeddings[0].values

            if is_valid_embedding(embedding):
                return list(embedding)

            actual_dimension = len(embedding) if embedding else 0
            logger.error(
                "Discarding invalid Gemini embedding from %s: expected %s dimensions, got %s.",
                settings.embedding_model,
                EMBEDDING_DIMENSION,
                actual_dimension,
            )
        except Exception as e:
            logger.warning(
                "Gemini embedding API call failed (%s): %s. No embedding will be stored.",
                settings.embedding_model,
                e,
            )

    return None


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
