"""
agents/relevance_agent.py
AGENT 1 - Relevance / Information Filtering Agent (Groq)

Reads the raw text the user submitted and decides whether it is genuinely
about a real-world crisis/disaster/emergency, strips duplicate/irrelevant
content, and hands clean text to the rest of the pipeline.
"""

import logging
from services.llm_service import LLMService, LLMServiceError
from utils.json_parser import extract_json

logger = logging.getLogger("crisis_agent.relevance_agent")

SYSTEM_PROMPT = """You are the Relevance Filtering Agent inside a multi-agent
crisis-information analysis system. Your ONLY job is to read the raw text
the user submitted and decide:
1. Is this text actually about a real-world crisis/disaster/emergency?
2. Remove any duplicate or repeated sentences.
3. Remove clearly irrelevant content (greetings, unrelated chit-chat, ads).

Respond ONLY with a JSON object in this exact format, with no extra text,
no markdown fences, and no commentary:

{
  "is_relevant": true or false,
  "reason": "short reason for your decision",
  "cleaned_text": "the cleaned, de-duplicated crisis-relevant text"
}

If the text is not relevant at all, set is_relevant to false and cleaned_text
to an empty string.
"""


class RelevanceAgent:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    def run(self, raw_text: str) -> dict:
        user_prompt = f"Raw report text:\n\n{raw_text}"

        try:
            raw_response = self.llm.generate(SYSTEM_PROMPT, user_prompt)
        except LLMServiceError as exc:
            logger.error("Relevance Agent LLM call failed: %s", exc)
            raise

        parsed = extract_json(raw_response)

        if not parsed:
            logger.warning("Relevance Agent: could not parse JSON, using raw text as-is.")
            return {
                "is_relevant": True,
                "reason": "Could not parse agent output; defaulting to relevant.",
                "cleaned_text": raw_text.strip(),
            }

        return {
            "is_relevant": bool(parsed.get("is_relevant", True)),
            "reason": parsed.get("reason", ""),
            "cleaned_text": parsed.get("cleaned_text", raw_text.strip()) or raw_text.strip(),
        }
