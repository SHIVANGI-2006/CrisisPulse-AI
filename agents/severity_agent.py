"""
agents/severity_agent.py
AGENT 4 - Severity Reasoning Agent (Groq)

Evaluates extracted facts and live verification notes to determine
severity level: LOW, MEDIUM, HIGH, or CRITICAL, with justification.
"""

import logging
import json
from services.llm_service import LLMService

logger = logging.getLogger("crisis_agent.severity_agent")

VALID_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]

SYSTEM_PROMPT = """You are the Severity Reasoning Agent in a multi-agent crisis intelligence system.
Evaluate the structured emergency facts and live verification details.
Determine a single severity level and concise justification.

Guidance:
- LOW: Minor localized issue, no casualties, minimal disruption.
- MEDIUM: Moderate impact, localized disruption, no confirmed casualties.
- HIGH: Significant impact, multiple areas affected, major disruption or injuries.
- CRITICAL: Confirmed fatalities, widespread destruction, or immediate threat to life.

Return ONLY a single valid JSON object matching this exact schema:
{
  "severity": "MEDIUM",
  "severity_reason": "concise 1-2 sentence justification"
}

The severity value MUST be exactly one of: "LOW", "MEDIUM", "HIGH", "CRITICAL".
Do not include markdown code fences, commentary, or text outside the JSON object.
"""


class SeverityAgent:
    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or LLMService()

    def run(self, extracted_facts: dict, verification_info: dict = None) -> dict:
        default_data = {
            "severity": "MEDIUM",
            "severity_reason": "Severity estimated as MEDIUM from available incident details.",
        }

        payload = dict(extracted_facts or {})
        if verification_info and isinstance(verification_info, dict):
            payload["live_verification_note"] = verification_info.get("verification_note", "")

        user_prompt = f"Structured crisis facts:\n\n{json.dumps(payload, indent=2)}"

        try:
            parsed = self.llm.generate_json(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=user_prompt,
                default_dict=default_data,
            )

            sev = str(parsed.get("severity", "MEDIUM")).strip().upper()
            if sev not in VALID_SEVERITIES:
                logger.warning("SeverityAgent received invalid severity '%s'. Defaulting to MEDIUM.", sev)
                sev = "MEDIUM"

            reason = str(parsed.get("severity_reason", "Severity assigned based on report facts.")).strip()

            return {
                "severity": sev,
                "severity_reason": reason,
            }
        except Exception as exc:
            logger.error("SeverityAgent encountered error: %s. Using default MEDIUM.", exc)
            return default_data
