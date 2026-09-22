"""
agents/orchestrator.py
Agent Orchestrator / Workflow Controller

Runs specialized agents in sequence:
  Relevance -> Extraction -> Live Verification (Tavily) -> Severity -> Summary

Tracks step-by-step status for the UI, applies fallback outputs if needed,
and assembles the final structured crisis briefing.
"""

import logging
from agents.relevance_agent import RelevanceAgent
from agents.extraction_agent import ExtractionAgent
from agents.verification_agent import VerificationAgent
from agents.severity_agent import SeverityAgent
from agents.summary_agent import SummaryAgent
from services.llm_service import LLMService
from services.tavily_service import TavilyService

logger = logging.getLogger("crisis_agent.orchestrator")


class OrchestratorError(Exception):
    """Raised when the agent pipeline cannot produce a valid result."""
    def __init__(self, message, agent_status=None):
        super().__init__(message)
        self.agent_status = agent_status or []


class AgentOrchestrator:
    def __init__(self, llm_service: LLMService = None, tavily_service: TavilyService = None):
        self.llm = llm_service or LLMService()
        self.tavily = tavily_service or TavilyService()
        self.relevance_agent = RelevanceAgent(self.llm)
        self.extraction_agent = ExtractionAgent(self.llm)
        self.verification_agent = VerificationAgent(self.llm, self.tavily)
        self.severity_agent = SeverityAgent(self.llm)
        self.summary_agent = SummaryAgent(self.llm)

    def run_pipeline(self, raw_text: str) -> dict:
        agent_status = []

        # ---- STEP 1: Relevance Agent ----
        try:
            relevance_result = self.relevance_agent.run(raw_text)
            agent_status.append({
                "agent": "Relevance / Filtering Agent",
                "status": "done",
                "detail": relevance_result.get("reason", "Analyzed report relevance."),
            })
        except Exception as exc:
            logger.error("Relevance Agent error: %s", exc)
            relevance_result = {
                "is_relevant": True,
                "reason": "Relevance fallback applied.",
                "cleaned_text": raw_text.strip(),
            }
            agent_status.append({
                "agent": "Relevance / Filtering Agent",
                "status": "done",
                "detail": "Fallback applied (LLM unavailable).",
            })

        if not relevance_result.get("is_relevant", True):
            agent_status.append({
                "agent": "Pipeline",
                "status": "stopped",
                "detail": "Input was judged not relevant to any crisis/disaster.",
            })
            return {"result": None, "agent_status": agent_status, "is_relevant": False}

        cleaned_text = relevance_result.get("cleaned_text") or raw_text.strip()

        # ---- STEP 2: Extraction Agent ----
        try:
            extracted = self.extraction_agent.run(cleaned_text)
            agent_status.append({
                "agent": "Information Extraction Agent",
                "status": "done",
                "detail": f"Identified crisis type: {extracted.get('crisis_type', 'Other')}",
            })
        except Exception as exc:
            logger.error("Extraction Agent error: %s", exc)
            extracted = {
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
            agent_status.append({
                "agent": "Information Extraction Agent",
                "status": "done",
                "detail": "Fallback facts applied.",
            })

        # ---- STEP 3: Live Verification Agent (Tavily) ----
        try:
            verification_info = self.verification_agent.run(extracted)
            v_status = "done" if verification_info.get("live_sources") else "skipped"
            agent_status.append({
                "agent": "Live Verification Agent (Tavily)",
                "status": v_status,
                "detail": verification_info.get("verification_note", ""),
            })
        except Exception as exc:
            logger.error("Verification Agent error: %s", exc)
            verification_info = {
                "corroborated": "unknown",
                "verification_note": "Live verification step skipped.",
                "live_sources": [],
            }
            agent_status.append({
                "agent": "Live Verification Agent (Tavily)",
                "status": "skipped",
                "detail": "Verification unavailable.",
            })

        # ---- STEP 4: Severity Reasoning Agent ----
        try:
            severity_info = self.severity_agent.run(extracted, verification_info)
            agent_status.append({
                "agent": "Severity Reasoning Agent",
                "status": "done",
                "detail": f"Severity assigned: {severity_info.get('severity', 'MEDIUM')}",
            })
        except Exception as exc:
            logger.error("Severity Agent error: %s", exc)
            severity_info = {
                "severity": "MEDIUM",
                "severity_reason": "Severity estimated from incident details.",
            }
            agent_status.append({
                "agent": "Severity Reasoning Agent",
                "status": "done",
                "detail": "Fallback severity applied.",
            })

        # ---- STEP 5: Summary & Action Agent ----
        try:
            summary_info = self.summary_agent.run(extracted, severity_info)
            agent_status.append({
                "agent": "Summary & Action Agent",
                "status": "done",
                "detail": "Summary, key points, and recommendations generated.",
            })
        except Exception as exc:
            logger.error("Summary Agent error: %s", exc)
            crisis_t = extracted.get("crisis_type", "Crisis")
            loc_t = extracted.get("location", "the area")
            sev_t = severity_info.get("severity", "MEDIUM")
            summary_info = {
                "summary": f"Emergency report regarding a {crisis_t.lower()} incident in {loc_t}.",
                "key_points": [f"Category: {crisis_t}", f"Location: {loc_t}"],
                "safety_recommendations": ["Follow instructions from local authorities."],
                "alert_message": f"{sev_t} PRIORITY — Emergency incident reported in {loc_t}.",
            }
            agent_status.append({
                "agent": "Summary & Action Agent",
                "status": "done",
                "detail": "Synthesized summary fallback.",
            })

        agent_status.append({
            "agent": "Final Emergency Briefing",
            "status": "done",
            "detail": "All agent outputs merged into final briefing.",
        })

        final_result = {
            **extracted,
            **verification_info,
            **severity_info,
            **summary_info,
        }

        return {"result": final_result, "agent_status": agent_status, "is_relevant": True}
