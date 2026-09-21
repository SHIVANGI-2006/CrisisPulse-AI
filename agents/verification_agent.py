"""
agents/verification_agent.py
AGENT 3 - Live Verification Agent (Tavily + Groq)  ** NEW **

This is what makes the pipeline genuinely "live": it takes the structured
facts already extracted, runs a real-time web search via Tavily to see if
any recent news corroborates the reported event, and asks Groq to write a
short, grounded verification note plus attach the source links.

If Tavily is not configured, this agent degrades gracefully: the rest of
the pipeline still runs, it just skips live corroboration.
"""

import logging

from services.tavily_service import TavilyService, TavilyServiceError
from services.llm_service import LLMService, LLMServiceError
from utils.json_parser import extract_json

logger = logging.getLogger("crisis_agent.verification_agent")

SYSTEM_PROMPT = """You are the Live Verification Agent inside a multi-agent
crisis-information analysis system. You are given structured facts already
extracted from a crisis report, plus live web search results gathered about
that event. Decide whether the live results corroborate the report and
write one or two grounded sentences explaining what they do or do not
confirm. Do not invent facts that are not present in the search results.

Respond ONLY with a JSON object in this exact format, no markdown fences,
no extra commentary:

{
  "corroborated": true or false,
  "verification_note": "one or two sentence note on what the live sources confirm or fail to confirm"
}
"""


class VerificationAgent:
    def __init__(self, llm_service: LLMService = None, tavily_service: TavilyService = None):
        self.llm = llm_service or LLMService()
        self.tavily = tavily_service or TavilyService()

    def run(self, extracted_facts: dict) -> dict:
        crisis_type = extracted_facts.get("crisis_type", "crisis")
        location = extracted_facts.get("location", "")
        query = f"{crisis_type} {location} latest news".strip()

        if not self.tavily.is_available():
            return {
                "corroborated": "unknown",
                "verification_note": "Live verification skipped — TAVILY_API_KEY is not configured.",
                "live_sources": [],
            }

        try:
            search_result = self.tavily.search_crisis(query)
        except TavilyServiceError as exc:
            logger.warning("Tavily search failed: %s", exc)
            return {
                "corroborated": "unknown",
                "verification_note": f"Live verification unavailable right now: {exc}",
                "live_sources": [],
            }

        sources = search_result.get("sources", [])
        if not sources:
            return {
                "corroborated": "unknown",
                "verification_note": "No matching live news sources were found for this event yet.",
                "live_sources": [],
            }

        user_prompt = (
            f"Structured crisis facts:\n{extracted_facts}\n\n"
            f"Live web search answer:\n{search_result.get('answer', '')}\n\n"
            "Live web search sources:\n"
            + "\n".join(f"- {s['title']}: {s['content']}" for s in sources)
        )

        try:
            raw = self.llm.generate(SYSTEM_PROMPT, user_prompt)
            parsed = extract_json(raw)
        except LLMServiceError as exc:
            logger.warning("Verification synthesis failed: %s", exc)
            parsed = {}

        corroborated = parsed.get("corroborated", "unknown")
        note = parsed.get(
            "verification_note",
            "Live sources were found but could not be automatically summarized.",
        )

        return {
            "corroborated": corroborated,
            "verification_note": note,
            "live_sources": sources[:4],
        }
