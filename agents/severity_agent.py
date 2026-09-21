"""
agents/severity_agent.py
AGENT 4 - Severity Reasoning Agent (Groq)

Reasons over the structured facts (and, when available, the live
verification note) and decides a severity level: LOW, MEDIUM, HIGH, or
CRITICAL, with a short justification.
"""

import logging
import json
from services.llm_service import LLMService, LLMServiceError
from utils.json_parser import extract_json

logger = logging.getLogger("crisis_agent.severity_agent")

VALID_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

SYSTEM_PROMPT = """You are the Severity Reasoning Agent inside a multi-agent
crisis-information analysis system. You are given structured facts already
extracted from a crisis report, and optionally a live verification note.
Reason step by step (internally) about how serious the situation is, then
decide a single severity level.

Guidance:
- LOW: minor/localized issue, no casualties, no major disruption.
- MEDIUM: moderate impact, some disruption, no confirmed casualties.
- HIGH: significant impact, multiple areas affected, evacuation or major
  disruption, possible injuries.
- CRITICAL: confirmed casualties/deaths, widespread destruction, or
  immediate life-threatening danger to many people.

Respond ONLY with a JSON object in this exact format, no markdown fences,
no extra commentary:

{
  "severity": "LOW" or "MEDIUM" or "HIGH" or "CRITICAL",
  "severity_reason": "one or two sentence explanation of your reasoning"
}
"""


class SeverityAgent:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    def run(self, extracted_facts: dict, verification_info: dict = None) -> dict:
        payload = dict(extracted_facts)
        if verification_info:
            payload["live_verification_note"] = verification_info.get("verification_note", "")

        user_prompt = (
            "Structured facts extracted from the crisis report:\n\n"
            f"{json.dumps(payload, indent=2)}"
        )

        try:
            raw_response = self.llm.generate(SYSTEM_PROMPT, user_prompt)
        except LLMServiceError as exc:
            logger.error("Severity Agent LLM call failed: %s", exc)
            raise

        parsed = extract_json(raw_response)

        severity = str(parsed.get("severity", "MEDIUM")).upper()
        if severity not in VALID_SEVERITIES:
            severity = "MEDIUM"

        return {
            "severity": severity,
            "severity_reason": parsed.get(
                "severity_reason", "Severity estimated from extracted facts."
            ),
        }
