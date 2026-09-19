"""
agents/extraction_agent.py
AGENT 2 - Information Extraction Agent (Groq)

Takes the cleaned text from the Relevance Agent and extracts structured
facts: crisis type, location, date/time, people affected, casualties,
infrastructure damage, transport disruption, evacuation info, etc.
"""

import logging
from services.llm_service import LLMService, LLMServiceError
from utils.json_parser import extract_json, safe_get_list

logger = logging.getLogger("crisis_agent.extraction_agent")

CRISIS_TYPES = [
    "Flood", "Earthquake", "Fire", "Cyclone", "Storm",
    "Landslide", "Heatwave", "Drought", "Other",
]

SYSTEM_PROMPT = f"""You are the Information Extraction Agent inside a
multi-agent crisis-information analysis system. Extract structured facts
from the crisis report text you are given.

The crisis_type MUST be one of exactly: {", ".join(CRISIS_TYPES)}.
If uncertain, use "Other".

Respond ONLY with a JSON object in this exact format, no markdown fences,
no extra commentary:

{{
  "crisis_type": "one of {CRISIS_TYPES}",
  "location": "best guess location, or 'Unknown'",
  "date_time": "date/time mentioned, or 'Not specified'",
  "affected_people": "description of people/population affected, or 'Unknown'",
  "casualties": "only if explicitly mentioned, otherwise 'None reported'",
  "infrastructure_damage": "description, or 'None reported'",
  "transport_disruption": "description, or 'None reported'",
  "evacuation_info": "description, or 'None reported'",
  "other_facts": ["short fact 1", "short fact 2"]
}}
"""


class ExtractionAgent:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    def run(self, cleaned_text: str) -> dict:
        user_prompt = f"Crisis report text:\n\n{cleaned_text}"

        try:
            raw_response = self.llm.generate(SYSTEM_PROMPT, user_prompt)
        except LLMServiceError as exc:
            logger.error("Extraction Agent LLM call failed: %s", exc)
            raise

        parsed = extract_json(raw_response)

        crisis_type = parsed.get("crisis_type", "Other")
        if crisis_type not in CRISIS_TYPES:
            crisis_type = "Other"

        return {
            "crisis_type": crisis_type,
            "location": parsed.get("location", "Unknown") or "Unknown",
            "date_time": parsed.get("date_time", "Not specified") or "Not specified",
            "affected_people": parsed.get("affected_people", "Unknown") or "Unknown",
            "casualties": parsed.get("casualties", "None reported") or "None reported",
            "infrastructure_damage": parsed.get("infrastructure_damage", "None reported") or "None reported",
            "transport_disruption": parsed.get("transport_disruption", "None reported") or "None reported",
            "evacuation_info": parsed.get("evacuation_info", "None reported") or "None reported",
            "other_facts": safe_get_list(parsed, "other_facts"),
        }
