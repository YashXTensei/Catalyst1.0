import json
import logging
import re
from typing import Dict, Any, Optional
from app.config import settings
from app.utils.embeddings import get_gemini_client

logger = logging.getLogger(__name__)


def clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Extracts JSON from text, stripping markdown code fences if present."""
    text = raw_text.strip()
    # Match ```json ... ``` or ``` ... ```
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        text = match.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        # Try to find the first { and last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except Exception:
                pass
        # Try finding array [ ... ]
        start_arr = text.find("[")
        end_arr = text.rfind("]")
        if start_arr != -1 and end_arr != -1 and end_arr > start_arr:
            try:
                return json.loads(text[start_arr:end_arr + 1])
            except Exception:
                pass
        logger.error(f"Failed to parse LLM JSON response: {text[:200]}")
        raise ValueError(f"Invalid JSON from model: {e}")


async def generate_json(
    prompt: str,
    system_instruction: Optional[str] = None,
    subsystem: str = "default",
) -> Any:
    """
    Calls Gemini API to generate structured JSON output.
    Uses model configured in GEMINI_MODEL (.env) and the client for the specified subsystem.
    """
    client = get_gemini_client(subsystem=subsystem)
    if not client or not settings.gemini_model:
        return None

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.2,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config,
        )

        if response and response.text:
            return clean_json_response(response.text)
        return None
    except Exception as e:
        logger.error(f"Error calling Gemini for structured JSON ({subsystem}, model: {settings.gemini_model}): {e}")
        return None


async def generate_text(
    prompt: str,
    system_instruction: Optional[str] = None,
    subsystem: str = "qa",
) -> str:
    """
    Calls Gemini API for text generation using GEMINI_MODEL from .env
    and the client for the specified subsystem (defaults to 'qa').
    """
    client = get_gemini_client(subsystem=subsystem)
    if not client or not settings.gemini_model:
        return ""

    try:
        from google.genai import types

        config = types.GenerateContentConfig(
            temperature=0.3,
        )
        if system_instruction:
            config.system_instruction = system_instruction

        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=config,
        )
        return response.text if response else ""
    except Exception as e:
        logger.error(f"Error calling Gemini for text generation ({subsystem}, model: {settings.gemini_model}): {e}")
        return ""
