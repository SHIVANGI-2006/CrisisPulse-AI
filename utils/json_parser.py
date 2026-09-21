"""
utils/json_parser.py
LLMs occasionally wrap JSON in markdown code fences or add stray commentary.
Groq's JSON mode makes this rare, but we keep a robust best-effort parser
as a safety net so the pipeline never hard-crashes on a formatting slip.
"""

import json
import re
import logging

logger = logging.getLogger("crisis_agent.json_parser")


def extract_json(raw_text: str) -> dict:
    if not raw_text or not raw_text.strip():
        return {}

    text = raw_text.strip()

    parsed = _try_parse(text)
    if parsed is not None:
        return parsed

    fenced = re.sub(r"^```(json)?", "", text, flags=re.IGNORECASE | re.MULTILINE)
    fenced = re.sub(r"```$", "", fenced, flags=re.MULTILINE).strip()
    parsed = _try_parse(fenced)
    if parsed is not None:
        return parsed

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

    logger.warning("Could not extract valid JSON from LLM output. Raw text: %.200s", text)
    return {}


def _try_parse(text: str):
    try:
        result = json.loads(text)
        if isinstance(result, dict):
            return result
        return None
    except (json.JSONDecodeError, TypeError):
        return None


def safe_get_list(data: dict, key: str) -> list:
    value = data.get(key, [])
    if isinstance(value, list):
        return [str(v) for v in value]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []
