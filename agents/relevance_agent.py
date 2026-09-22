"""
agents/relevance_agent.py
AGENT 1 - Relevance / Information Filtering Agent (Groq)

Decides if raw input is genuinely about a real-world crisis/disaster/emergency,
strips duplicate/irrelevant content, and returns clean text for the pipeline.
"""

import logging
from services.llm_service import LLMService

logger = logging.getLogger("crisis_agent.relevance_agent")

SYSTEM_PROMPT = """You are the Relevance Filtering Agent in a multi-agent crisis intelligence system.
Your task is to analyze the raw emergency report text and decide:
1. Is this text about a real-world crisis, disaster, or emergency situation?
2. Remove duplicate or repeated sentences.
3. Remove irrelevant conversational chit-chat.

Return ONLY a single valid JSON object matching this exact schema:
{
  "is_relevant": true,
  "reason": "short explanation of your decision",
  "cleaned_text": "cleaned, de-duplicated emergency text"
}

Do not include markdown code fences, commentary, or text outside the JSON object.
If the text is not a crisis or emergency, set is_relevant to false and cleaned_text to "".
"""


class RelevanceAgent:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    def run(self, raw_text: str) -> dict:
        fallback_data = {
            "is_relevant": True,
            "reason": "Relevance check default applied.",
            "cleaned_text": (raw_text or "").strip(),
        }

        if not raw_text or not raw_text.strip():
            return {
                "is_relevant": False,
                "reason": "No text provided.",
                "cleaned_text": "",
            }

        user_prompt = f"Raw emergency report text:\n\n{raw_text.strip()}"

        try:
            parsed = self.llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                default_dict=fallback_data,
            )
            is_rel = parsed.get("is_relevant")
            if is_rel is None:
                is_rel = True

            cleaned = parsed.get("cleaned_text", "")
            if is_rel and not cleaned.strip():
                cleaned = raw_text.strip()

            return {
                "is_relevant": bool(is_rel),
                "reason": str(parsed.get("reason", "Analysis completed.")),
                "cleaned_text": str(cleaned).strip(),
            }
        except Exception as exc:
            logger.error("RelevanceAgent encountered error: %s. Using fallback.", exc)
            return fallback_data
