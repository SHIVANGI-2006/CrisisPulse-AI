"""
services/demo_data.py
Canned example output so the app is explorable even before a GROQ_API_KEY
(and optionally TAVILY_API_KEY) has been added to .env.
"""

DEMO_AGENT_STATUS = [
    {"agent": "Relevance / Filtering Agent", "status": "demo", "detail": "Demo mode — skipped live call."},
    {"agent": "Information Extraction Agent", "status": "demo", "detail": "Demo mode — skipped live call."},
    {"agent": "Live Verification Agent (Tavily)", "status": "demo", "detail": "Demo mode — skipped live call."},
    {"agent": "Severity Reasoning Agent", "status": "demo", "detail": "Demo mode — skipped live call."},
    {"agent": "Summary & Action Agent", "status": "demo", "detail": "Demo mode — skipped live call."},
]


def get_demo_result(raw_text: str) -> dict:
    return {
        "crisis_type": "Flood",
        "location": "Mumbai, Maharashtra",
        "date_time": "Not specified",
        "affected_people": "Several thousand residents in low-lying neighborhoods",
        "casualties": "None reported",
        "infrastructure_damage": "Multiple roads flooded; public transport disrupted",
        "transport_disruption": "Suburban rail and bus routes suspended in affected zones",
        "evacuation_info": "Families relocated to nearby relief shelters",
        "other_facts": [
            "This is a DEMO result — add GROQ_API_KEY to .env for live analysis.",
        ],
        "corroborated": "unknown",
        "verification_note": "Demo mode — live Tavily verification is disabled. Add TAVILY_API_KEY to enable it.",
        "live_sources": [],
        "severity": "HIGH",
        "severity_reason": "Significant disruption across multiple areas with active evacuations, though no confirmed casualties.",
        "summary": (
            "Heavy rainfall has caused severe flooding across several low-lying areas of Mumbai, "
            "disrupting road and rail transport. Emergency teams are assisting residents, and "
            "several families have been evacuated to relief shelters as a precaution."
        ),
        "key_points": [
            "Widespread flooding in low-lying neighborhoods",
            "Public transport (rail & bus) suspended in affected zones",
            "Evacuations underway to relief shelters",
            "No casualties reported so far",
        ],
        "safety_recommendations": [
            "Avoid non-essential travel through flooded areas",
            "Follow evacuation orders from local authorities",
            "Keep mobile devices charged and monitor official alerts",
            "Avoid walking or driving through moving flood water",
        ],
        "alert_message": "HIGH PRIORITY — Active flooding and evacuations underway in Mumbai; avoid affected zones.",
    }
