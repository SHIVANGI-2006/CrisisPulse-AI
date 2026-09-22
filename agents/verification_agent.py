"""
agents/verification_agent.py
AGENT 3 - Live Verification Agent (Tavily + Groq)

Performs a real-time web search via Tavily using extracted crisis type & location.
Synthesizes a short grounded verification note with source links.
Gracefully degrades if Tavily API or LLM calls are unavailable.
"""

import logging
from services.tavily_service import TavilyService
from services.llm_service import LLMService

logger = logging.getLogger("crisis_agent.verification_agent")

SYSTEM_PROMPT = """You are the Live Verification Agent in a multi-agent crisis intelligence system.
Analyze extracted emergency report facts and live web search results.
Decide whether live news corroborates the report and write 1-2 grounded sentences explaining the findings.

Return ONLY a single valid JSON object matching this exact schema:
{
  "corroborated": true,
  "verification_note": "one or two sentence summary of live verification findings"
}

Do not include markdown code fences, commentary, or text outside the JSON object.
"""


class VerificationAgent:
    def __init__(self, llm_service: LLMService = None, tavily_service: TavilyService = None):
        self.llm = llm_service or LLMService()
        self.tavily = tavily_service or TavilyService()

    def run(self, extracted_facts: dict) -> dict:
        default_output = {
            "corroborated": "unknown",
            "verification_note": "Live verification skipped — TAVILY_API_KEY is not configured.",
            "live_sources": [],
        }

        if not self.tavily.is_available():
            return default_output

        crisis_type = extracted_facts.get("crisis_type", "crisis")
        location = extracted_facts.get("location", "")
        query = f"{crisis_type} {location} latest news".strip()

        try:
            search_result = self.tavily.search_crisis(query)
        except Exception as exc:
            logger.warning("Tavily search failed: %s", exc)
            return {
                "corroborated": "unknown",
                "verification_note": f"Live verification unavailable: {exc}",
                "live_sources": [],
            }

        sources = search_result.get("sources", [])
        if not sources:
            return {
                "corroborated": "unknown",
                "verification_note": "No matching live news sources were found for this event.",
                "live_sources": [],
            }

        user_prompt = (
            f"Extracted crisis facts:\n{extracted_facts}\n\n"
            f"Live web search answer:\n{search_result.get('answer', '')}\n\n"
            "Live web search sources:\n"
            + "\n".join(f"- {s.get('title', 'Source')}: {s.get('content', '')}" for s in sources)
        )

        try:
            parsed = self.llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                default_dict={"corroborated": "unknown", "verification_note": "Live news sources retrieved."},
            )

            corroborated_raw = parsed.get("corroborated", "unknown")
            if isinstance(corroborated_raw, bool):
                corroborated = "true" if corroborated_raw else "false"
            else:
                corroborated = str(corroborated_raw).lower()

            note = str(parsed.get("verification_note", "Live sources located.")).strip()

            return {
                "corroborated": corroborated,
                "verification_note": note,
                "live_sources": sources[:4],
            }
        except Exception as exc:
            logger.warning("Verification synthesis failed: %s", exc)
            return {
                "corroborated": "unknown",
                "verification_note": "Live search completed; synthesis summary unavailable.",
                "live_sources": sources[:4],
            }
