"""
agents/summary_agent.py
AGENT 5 - Summary & Action Agent (Groq)

Generates executive situation summary, key impact points, safety recommendations,
and a priority alert message based on extracted facts and severity level.
"""

import logging
import json
from services.llm_service import LLMService
from utils.json_parser import safe_get_list

logger = logging.getLogger("crisis_agent.summary_agent")

SYSTEM_PROMPT = """You are the Summary & Action Agent in a multi-agent crisis intelligence system.
Communicate the crisis situation clearly:
1. Write a concise 2-4 sentence executive summary.
2. List 3-5 key impact points (short facts).
3. List 3-5 practical safety & action recommendations.
4. Write a single-sentence alert message (starting with 'HIGH PRIORITY —' or 'CRITICAL PRIORITY —' if severity is HIGH/CRITICAL, or a calm advisory message if LOW/MEDIUM).

Return ONLY a single valid JSON object matching this exact schema:
{
  "summary": "2-4 sentence summary of the crisis situation",
  "key_points": ["key point 1", "key point 2", "key point 3"],
  "safety_recommendations": ["action 1", "action 2", "action 3"],
  "alert_message": "priority alert string"
}

Do not include markdown code fences, commentary, or text outside the JSON object.
"""


class SummaryAgent:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    def run(self, extracted_facts: dict, severity_info: dict) -> dict:
        crisis_type = extracted_facts.get("crisis_type", "Crisis")
        location = extracted_facts.get("location", "the affected area")
        sev = severity_info.get("severity", "MEDIUM")

        fallback_summary = {
            "summary": f"Emergency report regarding a {crisis_type.lower()} incident in {location}. Severity level: {sev}.",
            "key_points": [
                f"Incident Category: {crisis_type}",
                f"Location: {location}",
                f"Casualties: {extracted_facts.get('casualties', 'None reported')}",
                f"Infrastructure Damage: {extracted_facts.get('infrastructure_damage', 'None reported')}",
            ],
            "safety_recommendations": [
                "Avoid non-essential travel to or through affected zones.",
                "Follow official directives from local emergency services.",
                "Keep emergency contact details and supplies accessible.",
            ],
            "alert_message": f"{sev} PRIORITY — Emergency incident reported in {location}. Exercise caution.",
        }

        combined_input = {**(extracted_facts or {}), **(severity_info or {})}
        user_prompt = f"Structured facts and severity evaluation:\n\n{json.dumps(combined_input, indent=2)}"

        try:
            parsed = self.llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                default_dict=fallback_summary,
            )

            summary = str(parsed.get("summary", "") or fallback_summary["summary"]).strip()
            key_points = safe_get_list(parsed, "key_points") or fallback_summary["key_points"]
            recs = safe_get_list(parsed, "safety_recommendations") or fallback_summary["safety_recommendations"]
            alert = str(parsed.get("alert_message", "") or fallback_summary["alert_message"]).strip()

            return {
                "summary": summary,
                "key_points": key_points,
                "safety_recommendations": recs,
                "alert_message": alert,
            }
        except Exception as exc:
            logger.error("SummaryAgent encountered error: %s. Using synthesized fallback.", exc)
            return fallback_summary
