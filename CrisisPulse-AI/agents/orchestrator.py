"""
agents/orchestrator.py
Agent Orchestrator / Workflow Controller

Runs each specialized agent IN SEQUENCE, passing the output of one as the
input to the next:

    Relevance -> Extraction -> Live Verification (Tavily) -> Severity -> Summary

It makes autonomous decisions along the way (e.g. it stops early if the
Relevance Agent decides the input isn't a real crisis), tracks per-step
status for the UI, and assembles the final structured briefing.
"""

import logging

from agents.relevance_agent import RelevanceAgent
from agents.extraction_agent import ExtractionAgent
from agents.verification_agent import VerificationAgent
from agents.severity_agent import SeverityAgent
from agents.summary_agent import SummaryAgent
from services.llm_service import LLMService, LLMServiceError
from services.tavily_service import TavilyService

logger = logging.getLogger("crisis_agent.orchestrator")


class OrchestratorError(Exception):
    """Raised when the agent pipeline cannot complete."""
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
                "detail": relevance_result.get("reason", ""),
            })
        except LLMServiceError as exc:
            agent_status.append({
                "agent": "Relevance / Filtering Agent",
                "status": "failed",
                "detail": str(exc),
            })
            raise OrchestratorError(str(exc), agent_status)

        if not relevance_result.get("is_relevant", True):
            agent_status.append({
                "agent": "Pipeline",
                "status": "stopped",
                "detail": "Input was judged not relevant to any crisis/disaster.",
            })
            return {"result": None, "agent_status": agent_status, "is_relevant": False}

        cleaned_text = relevance_result.get("cleaned_text") or raw_text

        # ---- STEP 2: Extraction Agent ----
        try:
            extracted = self.extraction_agent.run(cleaned_text)
            agent_status.append({
                "agent": "Information Extraction Agent",
                "status": "done",
                "detail": f"Identified crisis type: {extracted.get('crisis_type')}",
            })
        except LLMServiceError as exc:
            agent_status.append({
                "agent": "Information Extraction Agent",
                "status": "failed",
                "detail": str(exc),
            })
            raise OrchestratorError(str(exc), agent_status)

        # ---- STEP 3: Live Verification Agent (Tavily) ----
        verification_info = self.verification_agent.run(extracted)
        v_status = "done" if verification_info.get("live_sources") else "skipped"
        agent_status.append({
            "agent": "Live Verification Agent (Tavily)",
            "status": v_status,
            "detail": verification_info.get("verification_note", ""),
        })

        # ---- STEP 4: Severity Reasoning Agent ----
        try:
            severity_info = self.severity_agent.run(extracted, verification_info)
            agent_status.append({
                "agent": "Severity Reasoning Agent",
                "status": "done",
                "detail": f"Severity assigned: {severity_info.get('severity')}",
            })
        except LLMServiceError as exc:
            agent_status.append({
                "agent": "Severity Reasoning Agent",
                "status": "failed",
                "detail": str(exc),
            })
            raise OrchestratorError(str(exc), agent_status)

        # ---- STEP 5: Summary & Action Agent ----
        try:
            summary_info = self.summary_agent.run(extracted, severity_info)
            agent_status.append({
                "agent": "Summary & Action Agent",
                "status": "done",
                "detail": "Summary, key points, and recommendations generated.",
            })
        except LLMServiceError as exc:
            agent_status.append({
                "agent": "Summary & Action Agent",
                "status": "failed",
                "detail": str(exc),
            })
            raise OrchestratorError(str(exc), agent_status)

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
