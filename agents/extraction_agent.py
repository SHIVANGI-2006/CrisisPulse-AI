"""
agents/extraction_agent.py
AGENT 2 - Information Extraction Agent (Groq)

Takes cleaned emergency text and extracts structured facts: crisis_type,
location, date_time, affected_people, casualties, infrastructure_damage,
transport_disruption, evacuation_info, and other_facts.
"""

import logging
from services.llm_service import LLMService
from utils.json_parser import safe_get_list

logger = logging.getLogger("crisis_agent.extraction_agent")

CRISIS_TYPES = [
    "Flood", "Earthquake", "Fire", "Cyclone", "Storm",
    "Landslide", "Heatwave", "Drought", "Other",
]

SYSTEM_PROMPT = f"""You are the Information Extraction Agent in a multi-agent crisis intelligence system.
Extract structured facts from the emergency report text provided.

The crisis_type MUST be one of exactly: {", ".join(CRISIS_TYPES)}. If uncertain, use "Other".

Return ONLY a single valid JSON object matching this exact schema:
{{
  "crisis_type": "Flood",
  "location": "location name or Unknown",
  "date_time": "time or Not specified",
  "affected_people": "details or Unknown",
  "casualties": "details or None reported",
  "infrastructure_damage": "details or None reported",
  "transport_disruption": "details or None reported",
  "evacuation_info": "details or None reported",
  "other_facts": ["fact 1", "fact 2"]
}}

Do not include markdown code fences, commentary, or text outside the JSON object.
"""


class ExtractionAgent:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    def run(self, cleaned_text: str) -> dict:
        default_data = {
            "crisis_type": "Other",
            "location": "Unknown",
            "date_time": "Not specified",
            "affected_people": "Unknown",
            "casualties": "None reported",
            "infrastructure_damage": "None reported",
            "transport_disruption": "None reported",
            "evacuation_info": "None reported",
            "other_facts": [],
        }

        if not cleaned_text or not cleaned_text.strip():
            return default_data

        user_prompt = f"Emergency report text:\n\n{cleaned_text.strip()}"

        try:
            parsed = self.llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                default_dict=default_data,
            )

            c_type = str(parsed.get("crisis_type", "Other")).strip()
            if c_type not in CRISIS_TYPES:
                # Case-insensitive check
                matched = next((t for t in CRISIS_TYPES if t.lower() == c_type.lower()), "Other")
                c_type = matched

            return {
                "crisis_type": c_type,
                "location": str(parsed.get("location", "Unknown") or "Unknown").strip(),
                "date_time": str(parsed.get("date_time", "Not specified") or "Not specified").strip(),
                "affected_people": str(parsed.get("affected_people", "Unknown") or "Unknown").strip(),
                "casualties": str(parsed.get("casualties", "None reported") or "None reported").strip(),
                "infrastructure_damage": str(parsed.get("infrastructure_damage", "None reported") or "None reported").strip(),
                "transport_disruption": str(parsed.get("transport_disruption", "None reported") or "None reported").strip(),
                "evacuation_info": str(parsed.get("evacuation_info", "None reported") or "None reported").strip(),
                "other_facts": safe_get_list(parsed, "other_facts"),
            }
        except Exception as exc:
            logger.error("ExtractionAgent encountered error: %s. Using default extraction.", exc)
            return default_data
