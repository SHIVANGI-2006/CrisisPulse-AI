"""
utils/json_parser.py
Robust best-effort JSON parser and safety net for LLM outputs.
Extracts JSON from plain text, markdown code fences, reasoning blocks, or surrounded text.
"""

import json
import re
import logging

logger = logging.getLogger("crisis_agent.json_parser")


def extract_json(raw_text: str) -> dict:
    """
    Extracts and returns a python dictionary from raw LLM output text.
    Handles:
      - Plain JSON string
      - Markdown code blocks (```json ... ``` or ``` ... ```)
      - Reasoning blocks (<think> ... </think>)
      - Text surrounding JSON objects
      - Minor JSON syntax flaws (trailing commas)
    Returns an empty dict {} if extraction fails.
    """
    if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
        return {}

    text = raw_text.strip()

    # 1. Strip reasoning blocks such as <think>...</think> produced by reasoning models
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE).strip()

    # 2. Try direct parse
    parsed = _try_parse(text)
    if parsed is not None:
        return parsed

    # 3. Try markdown fenced code blocks: ```json { ... } ``` or ``` { ... } ```
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        parsed = _try_parse(fenced_match.group(1))
        if parsed is not None:
            return parsed

    # 4. Strip leading/trailing code fences if present
    fenced_clean = re.sub(r"^```(?:json)?", "", text, flags=re.IGNORECASE | re.MULTILINE)
    fenced_clean = re.sub(r"```$", "", fenced_clean, flags=re.MULTILINE).strip()
    parsed = _try_parse(fenced_clean)
    if parsed is not None:
        return parsed

    # 5. Search for balanced curly braces { ... }
    start = text.find("{")
    if start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    parsed = _try_parse(candidate)
                    if parsed is not None:
                        return parsed
                    break

    logger.warning("Could not extract valid JSON from LLM output. Snippet: %.200s", text)
    return {}


def _try_parse(text: str):
    if not text:
        return None
    text = text.strip()
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
        return None
    except (json.JSONDecodeError, TypeError):
        # Attempt simple fix for trailing commas before closing braces/brackets
        try:
            cleaned = re.sub(r",\s*([}\]])", r"\1", text)
            result = json.loads(cleaned)
            if isinstance(result, dict):
                return result
        except Exception:
            pass
        return None


def safe_get_list(data: dict, key: str) -> list:
    """Safely extracts a list of strings from a dictionary key."""
    if not isinstance(data, dict):
        return []
    value = data.get(key, [])
    if isinstance(value, list):
        return [str(v).strip() for v in value if v is not None and str(v).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
