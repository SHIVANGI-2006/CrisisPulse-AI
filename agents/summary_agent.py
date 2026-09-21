"""
agents/summary_agent.py
AGENT 5 - Summary & Action Agent (Groq)

Given the extracted facts and the severity decision, produces a concise
summary, key points, safety recommendations, and a priority alert message.
Runs last so it can focus purely on clear communication.
"""

import logging
import json
from services.llm_service import LLMService, LLMServiceError
from utils.json_parser import extract_json, safe_get_list

logger = logging.getLogger("crisis_agent.summary_agent")

SYSTEM_PROMPT = """You are the Summary & Action Agent inside a multi-agent
crisis-information analysis system. You are given structured facts and a
severity decision already made by earlier agents. Your job is ONLY to
communicate this clearly:

1. Write a concise 2-4 sentence summary of the situation.
2. List 3-6 short key points (bullet-style facts).
3. List 3-6 practical safety recommendations for people in the affected area.
4. Write a short one-sentence alert_message. If severity is HIGH or
   CRITICAL, start it with "HIGH PRIORITY —" or "CRITICAL PRIORITY —"
   respectively. If LOW or MEDIUM, write a calmer advisory-style message.

Respond ONLY with a JSON object in this exact format, no markdown fences,
no extra commentary:

{
  "summary": "...",
  "key_points": ["...", "...", "..."],
  "safety_recommendations": ["...", "...", "..."],
  "alert_message": "..."
}
"""


class SummaryAgent:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    def run(self, extracted_facts: dict, severity_info: dict) -> dict:
        combined_input = {**extracted_facts, **severity_info}
        user_prompt = (
            "Structured facts and severity decision:\n\n"
            f"{json.dumps(combined_input, indent=2)}"
        )

        try:
            raw_response = self.llm.generate(SYSTEM_PROMPT, user_prompt)
            parsed = extract_json(raw_response)
        except LLMServiceError as exc:
            logger.warning("Summary Agent LLM call failed. Synthesizing fallback summary: %s", exc)
            crisis_type = extracted_facts.get("crisis_type", "Crisis")
            location = extracted_facts.get("location", "the affected area")
            sev = severity_info.get("severity", "MEDIUM")
            parsed = {
                "summary": f"Emergency report regarding a {crisis_type.lower()} incident in {location}. Severity level: {sev}.",
                "key_points": [
                    f"Incident Type: {crisis_type}",
                    f"Location: {location}",
                    f"Casualties: {extracted_facts.get('casualties', 'None reported')}",
                    f"Infrastructure Damage: {extracted_facts.get('infrastructure_damage', 'None reported')}",
                ],
                "safety_recommendations": [
                    "Avoid traveling to or through affected zones.",
                    "Follow official directives from local authorities.",
                    "Keep emergency contact details accessible.",
                ],
                "alert_message": f"{sev} PRIORITY — Emergency incident reported in {location}. Exercise caution.",
            }

        return {
            "summary": parsed.get("summary", "Summary could not be generated."),
            "key_points": safe_get_list(parsed, "key_points"),
            "safety_recommendations": safe_get_list(parsed, "safety_recommendations"),
            "alert_message": parsed.get("alert_message", "No alert message generated."),
        }
