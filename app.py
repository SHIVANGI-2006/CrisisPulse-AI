"""
app.py
CrisisPulse AI — Multi-Agent Crisis Intelligence System
Frontend: Gradio + custom CSS/JS  |  Backend: Python + Groq + Tavily

Pipeline: Relevance -> Extraction -> Live Verification (Tavily) -> Severity -> Summary
No Ollama or any local model server is used — Groq (LLM) and Tavily (live
web search) are the only external APIs this project talks to.
"""

import logging
import os

import gradio as gr

from config import config
from services.database_service import DatabaseService
from services.llm_service import LLMService
from services.tavily_service import TavilyService
from services.demo_data import get_demo_result, DEMO_AGENT_STATUS
from agents.orchestrator import AgentOrchestrator, OrchestratorError
from utils.text_utils import validate_report_text, clean_text, allowed_file
from services.pdf_service import generate_crisis_pdf

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("crisis_agent.app")

# ---------- Core services ----------
db = DatabaseService()
llm_service = LLMService()
tavily_service = TavilyService()
orchestrator = AgentOrchestrator(llm_service, tavily_service)

logger.info(
    "CrisisPulse AI starting up. Groq model: %s | Groq configured: %s | Tavily configured: %s | DB backend: %s",
    config.GROQ_MODEL, llm_service.is_available(), tavily_service.is_available(), db.backend_label,
)

# ---------- Sample Disaster Reports ----------
SAMPLE_REPORTS = {
    "🌊 Flood (Mumbai)": (
        "Heavy rainfall has caused severe flooding in several low-lying areas of Mumbai. "
        "Multiple roads are closed and public transportation has been disrupted. "
        "Emergency teams are assisting residents in vulnerable locations, and authorities have "
        "advised residents to avoid unnecessary travel. Several families in low-lying neighborhoods "
        "are being evacuated to relief shelters."
    ),
    "🏚️ Earthquake (Anjar)": (
        "A magnitude 6.1 earthquake struck near the coastal town of Anjar early this morning. "
        "Several old buildings have collapsed and at least 12 people are reported injured. "
        "Aftershocks are expected over the next 24 hours. Local hospitals are treating the injured "
        "and rescue teams are searching damaged structures for anyone trapped."
    ),
    "🔥 Industrial Fire (Pune)": (
        "A large fire broke out at a commercial warehouse complex in the industrial area of Pune late last night. "
        "Firefighters worked for over six hours to bring the blaze under control. "
        "No casualties have been reported, but nearby residents were temporarily evacuated as a precaution due to heavy smoke."
    ),
    "🌀 Cyclone (Gujarat Coast)": (
        "Cyclone Biparjoy is expected to make landfall near the Gujarat coast within the next 12 hours, "
        "bringing wind speeds of up to 150 km/h. Coastal villages have been evacuated and fishermen "
        "have been advised not to venture into the sea. Power supply in several districts has already been "
        "disrupted as a precaution."
    ),
    "☀️ Heatwave (Rajasthan)": (
        "A prolonged heatwave has pushed temperatures above 45 degrees Celsius across several districts "
        "of Rajasthan for the fifth consecutive day. Hospitals are reporting a rise in heatstroke cases, "
        "mostly among elderly residents and outdoor laborers. Authorities have issued an advisory urging "
        "people to stay indoors during peak afternoon hours."
    ),
    "☕ Non-Crisis Control": (
        "Just wanted to say the new coffee shop downtown has amazing pastries and the weather has been "
        "really pleasant lately for a walk in the park."
    ),
}

# ---------- Custom CSS ----------
CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --cp-bg: #05070d;
    --cp-panel: #0d1220;
    --cp-panel-2: #121a2e;
    --cp-border: rgba(148, 163, 184, 0.14);
    --cp-accent: #6366f1;
    --cp-accent-2: #22d3ee;
    --cp-text: #e2e8f0;
    --cp-muted: #94a3b8;
}

.gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    max-width: 1400px !important;
    margin: 0 auto !important;
}

body, .gradio-container.dark, .gradio-container {
    background: radial-gradient(circle at 15% 0%, #12183a 0%, #05070d 45%), var(--cp-bg) !important;
}

h1, h2, h3, .prose h1, .prose h2, .prose h3 {
    font-family: 'Space Grotesk', 'Inter', sans-serif !important;
}

/* ---------- Hero header ---------- */
.cp-hero {
    position: relative;
    width: 100%;
    border-radius: 20px;
    padding: 34px 36px;
    margin-bottom: 22px;
    overflow: hidden;
    background:
        radial-gradient(circle at 0% 0%, rgba(99,102,241,0.35), transparent 55%),
        radial-gradient(circle at 100% 0%, rgba(34,211,238,0.28), transparent 55%),
        linear-gradient(135deg, #0b0f1f 0%, #0d1a2b 100%);
    border: 1px solid var(--cp-border);
    box-shadow: 0 20px 50px rgba(0,0,0,0.45);
}
.cp-hero::after {
    content: "";
    position: absolute;
    inset: 0;
    background-image: radial-gradient(rgba(255,255,255,0.05) 1px, transparent 1px);
    background-size: 22px 22px;
    opacity: 0.4;
    pointer-events: none;
}
.cp-hero-inner { position: relative; z-index: 1; display: flex; align-items: center; gap: 20px; flex-wrap: wrap; }
.cp-badge-pulse {
    width: 58px; height: 58px; border-radius: 16px; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center; font-size: 28px;
    background: linear-gradient(135deg, var(--cp-accent), var(--cp-accent-2));
    box-shadow: 0 0 30px rgba(99,102,241,0.55);
    animation: cpPulse 2.6s ease-in-out infinite;
}
@keyframes cpPulse {
    0%, 100% { box-shadow: 0 0 22px rgba(99,102,241,0.45); }
    50% { box-shadow: 0 0 40px rgba(34,211,238,0.65); }
}
.cp-hero-title { font-size: 28px; font-weight: 700; color: #f8fafc; margin: 0; letter-spacing: -0.02em; }
.cp-hero-sub { color: var(--cp-muted); font-size: 14.5px; margin-top: 4px; }
.cp-chip-row { display: flex; gap: 8px; margin-top: 12px; flex-wrap: wrap; }
.cp-chip {
    font-size: 11.5px; font-weight: 600; padding: 5px 12px; border-radius: 999px;
    border: 1px solid var(--cp-border); color: var(--cp-text);
    background: rgba(148,163,184,0.08); letter-spacing: 0.02em;
}
.cp-chip.groq { border-color: rgba(99,102,241,0.5); color: #c7d2fe; }
.cp-chip.tavily { border-color: rgba(34,211,238,0.5); color: #a5f3fc; }
.cp-chip.db { border-color: rgba(74,222,128,0.5); color: #bbf7d0; }

/* ---------- Cards / panels ---------- */
.cp-panel {
    background: var(--cp-panel) !important;
    border: 1px solid var(--cp-border) !important;
    border-radius: 16px !important;
    padding: 4px !important;
}

/* ---------- Severity badges ---------- */
.severity-badge-CRITICAL { background: linear-gradient(135deg, #dc2626, #991b1b); color: #fff; padding: 6px 16px; border-radius: 20px; font-weight: 700; box-shadow: 0 0 15px rgba(220,38,38,0.6); }
.severity-badge-HIGH { background: linear-gradient(135deg, #ea580c, #c2410c); color: #fff; padding: 6px 16px; border-radius: 20px; font-weight: 700; box-shadow: 0 0 12px rgba(234,88,12,0.5); }
.severity-badge-MEDIUM { background: linear-gradient(135deg, #eab308, #ca8a04); color: #000; padding: 6px 16px; border-radius: 20px; font-weight: 700; }
.severity-badge-LOW { background: linear-gradient(135deg, #16a34a, #15803d); color: #fff; padding: 6px 16px; border-radius: 20px; font-weight: 700; }

/* ---------- Buttons ---------- */
.sample-btn { border-radius: 10px !important; transition: all 0.18s ease !important; border: 1px solid var(--cp-border) !important; }
.sample-btn:hover { transform: translateY(-2px); border-color: var(--cp-accent) !important; }

#cp-run-btn { background: linear-gradient(135deg, var(--cp-accent), var(--cp-accent-2)) !important; border: none !important; font-weight: 700 !important; box-shadow: 0 8px 24px rgba(99,102,241,0.35) !important; }
#cp-run-btn:hover { transform: translateY(-1px); box-shadow: 0 12px 30px rgba(34,211,238,0.4) !important; }

/* ---------- Misc ---------- */
.cp-footnote { color: var(--cp-muted); font-size: 12px; text-align: center; margin-top: 18px; }
"""

CUSTOM_JS = """
() => {
    // Subtle entrance animation for the hero block, purely cosmetic.
    const hero = document.querySelector('.cp-hero');
    if (hero) {
        hero.style.opacity = 0;
        hero.style.transform = 'translateY(-8px)';
        requestAnimationFrame(() => {
            hero.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
            hero.style.opacity = 1;
            hero.style.transform = 'translateY(0)';
        });
    }
}
"""

# ---------- Core Analysis Logic ----------

def _run_analysis(raw_text: str, source: str = "manual"):
    """Returns (analysis_id, result_dict, agent_status, demo_mode_used, error_message)."""
    try:
        is_valid, error = validate_report_text(raw_text)
        if not is_valid:
            return None, None, [], False, error

        cleaned = clean_text(raw_text)
        report_id = db.save_report(cleaned, source=source)

        if not llm_service.is_available():
            if config.DEMO_MODE:
                demo_result = get_demo_result(cleaned)
                analysis_id = db.save_analysis(report_id, demo_result, demo_mode=True)
                return analysis_id, demo_result, DEMO_AGENT_STATUS, True, None
            return None, None, [], False, (
                "GROQ_API_KEY is not configured. Add it to your .env file, or enable "
                "DEMO_MODE=true to explore the app with sample data."
            )

        try:
            pipeline_output = orchestrator.run_pipeline(cleaned)
        except OrchestratorError as exc:
            logger.error("Pipeline failed: %s", exc)
            return None, None, exc.agent_status, False, str(exc)

        if not pipeline_output["is_relevant"]:
            return None, None, pipeline_output["agent_status"], False, (
                "The submitted text was judged NOT relevant to any crisis or disaster. "
                "Please provide an actual crisis/emergency report."
            )

        result = pipeline_output["result"]
        analysis_id = db.save_analysis(report_id, result, demo_mode=False)
        return analysis_id, result, pipeline_output["agent_status"], False, None
    except Exception as exc:
        logger.error("Unexpected error in _run_analysis: %s", exc, exc_info=True)
        return None, None, [], False, f"An error occurred during processing: {str(exc)}"


# ---------- Formatting Helpers ----------

SEVERITY_EMOJI = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🟠", "CRITICAL": "🔴"}


def _format_agent_status(agent_status):
    if not agent_status:
        return ""
    lines = ["### 🧭 Multi-Agent Workflow Execution Status\n"]
    icon = {"done": "✅", "failed": "❌", "stopped": "⏹️", "demo": "🧪", "skipped": "⚪"}
    for step in agent_status:
        lines.append(
            f"- {icon.get(step.get('status'), '•')} **{step.get('agent')}** "
            f"(`{step.get('status')}`) — {step.get('detail', '')}"
        )
    return "\n".join(lines)


def _format_result(analysis_id, result, demo_used):
    if not result:
        return ""

    sev = str(result.get("severity", "MEDIUM")).upper()
    emoji = SEVERITY_EMOJI.get(sev, "⚪")

    other_facts = result.get("other_facts", []) or []
    key_points = result.get("key_points", []) or []
    recs = result.get("safety_recommendations", []) or []
    live_sources = result.get("live_sources", []) or []
    corroborated = str(result.get("corroborated", "unknown")).lower()

    lines = []
    if demo_used:
        lines.append("> 🧪 **DEMO MODE** — Groq/Tavily not configured; showing sample output. Add your API keys to `.env` for live analysis.\n")

    lines.append(f"## {emoji} Emergency Level: **{sev}**")
    lines.append(f"*Analysis ID: #{analysis_id}*\n")
    lines.append(f"> 🚨 **ALERT:** {result.get('alert_message', 'No immediate alert string provided.')}\n")

    lines.append("### 📋 Executive Situation Summary")
    lines.append(result.get("summary", "") + "\n")

    lines.append("### 🔎 Key Extracted Facts")
    lines.append(f"- 🏷️ **Crisis Type:** `{result.get('crisis_type', 'Other')}`")
    lines.append(f"- 📍 **Location:** {result.get('location', 'Unknown')}")
    lines.append(f"- 🕒 **Timestamp:** {result.get('date_time', 'Not specified')}")
    lines.append(f"- 👥 **Affected Population:** {result.get('affected_people', 'Unknown')}")
    lines.append(f"- 🚑 **Casualties / Injuries:** {result.get('casualties', 'None reported')}")
    lines.append(f"- 🏗️ **Infrastructure Damage:** {result.get('infrastructure_damage', 'None reported')}")
    lines.append(f"- 🚗 **Transport Disruption:** {result.get('transport_disruption', 'None reported')}")
    if other_facts:
        lines.append("- 📌 **Additional Key Details:**")
        for f in other_facts:
            lines.append(f"  - {f}")
    lines.append("")

    lines.append(f"### 🧠 Severity Assessment Rationale\n{result.get('severity_reason', '')}\n")

    # Live Verification (Tavily) section
    verification_note = result.get("verification_note")
    if verification_note:
        badge = {"true": "✅ Corroborated by live sources", "false": "⚠️ Not corroborated"}.get(
            corroborated, "ℹ️ Unverified / no live match"
        )
        lines.append(f"### 🌐 Live Verification (Tavily) — {badge}")
        lines.append(verification_note + "\n")
        if live_sources:
            lines.append("**Live sources:**")
            for s in live_sources:
                title = s.get("title", "Source")
                url = s.get("url", "")
                if url:
                    lines.append(f"- [{title}]({url})")
        lines.append("")

    if key_points:
        lines.append("### 🔑 Key Emergency Points")
        for k in key_points:
            lines.append(f"- {k}")
        lines.append("")

    if recs:
        lines.append("### ✅ Recommended Safety Actions")
        for r in recs:
            lines.append(f"- {r}")
        lines.append("")

    return "\n".join(lines)


# ---------- Gradio Callbacks ----------

def analyze_callback(report_text, uploaded_file):
    try:
        raw_text = (report_text or "").strip()
        source = "manual"

        if uploaded_file is not None:
            filename = os.path.basename(uploaded_file)
            if not allowed_file(filename):
                return "❌ Only `.txt` or `.pdf` files are allowed.", "*Analysis aborted due to invalid file type.*", None, gr.update(visible=False)
            try:
                if filename.lower().endswith(".txt"):
                    with open(uploaded_file, "r", encoding="utf-8", errors="ignore") as f:
                        raw_text = f.read()
                    source = f"file:{filename}"
                elif filename.lower().endswith(".pdf"):
                    from pypdf import PdfReader
                    reader = PdfReader(uploaded_file)
                    raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
                    source = f"file:{filename}"
            except Exception as exc:
                logger.error("File extraction failed: %s", exc)
                return "❌ Could not read the uploaded file.", "*File extraction failed.*", None, gr.update(visible=False)

        if not raw_text.strip():
            return "❌ Please enter a crisis report or upload a document.", "*No input provided.*", None, gr.update(visible=False)

        analysis_id, result, agent_status, demo_used, error = _run_analysis(raw_text, source=source)
        status_md = _format_agent_status(agent_status)

        if error:
            return f"❌ **{error}**", status_md or "*Pipeline stopped.*", None, gr.update(visible=False)

        result_md = _format_result(analysis_id, result, demo_used)

        try:
            pdf_file_path = generate_crisis_pdf(analysis_id, result)
            pdf_update = gr.update(value=pdf_file_path, visible=True)
        except Exception as exc:
            logger.error("PDF generation failed: %s", exc)
            pdf_update = gr.update(visible=False)

        return result_md, status_md, analysis_id, pdf_update
    except Exception as exc:
        logger.error("Error in analyze_callback: %s", exc, exc_info=True)
        return f"❌ **System Error:** {str(exc)}", "*Execution failed.*", None, gr.update(visible=False)


def load_history_callback(severity_filter="ALL"):
    records = db.get_history(limit=200)
    if not records:
        return [["—", "—", "—", "—", "—"]]
    rows = []
    for r in records:
        sev = r.get("severity", "")
        if severity_filter != "ALL" and sev != severity_filter:
            continue
        rows.append([r.get("id"), r.get("crisis_type"), r.get("location"), sev, r.get("created_at")])
    return rows or [["—", "No matching records", "—", "—", "—"]]


def load_result_by_id_callback(analysis_id):
    if analysis_id is None:
        return "Enter an Analysis ID above and click 'Load Result'.", None
    try:
        analysis_id = int(analysis_id)
    except (TypeError, ValueError):
        return "Please enter a valid numeric Analysis ID.", None
    result = db.get_result_by_id(analysis_id)
    if not result:
        return f"No analysis found with ID #{analysis_id}.", None

    result_md = _format_result(analysis_id, result, bool(result.get("demo_mode")))
    try:
        pdf_path = generate_crisis_pdf(analysis_id, result)
        pdf_update = gr.update(value=pdf_path, visible=True)
    except Exception:
        pdf_update = gr.update(visible=False)

    return result_md, pdf_update


def load_dashboard_callback():
    stats = db.get_dashboard_stats()

    lines = ["### ⚡ System Operational Status"]
    lines.append(f"- **Groq LLM Engine:** {'🟢 Configured & Ready' if llm_service.is_available() else '🔴 Not configured (using Demo Mode)'}")
    lines.append(f"- **Configured Groq Model:** `{config.GROQ_MODEL}`")
    lines.append(f"- **Tavily Live Verification:** {'🟢 Configured & Ready' if tavily_service.is_available() else '⚪ Not configured (verification step will be skipped)'}")
    lines.append(f"- **Database Backend:** `{stats['backend_label']}`")
    lines.append(f"- **Demo Mode Fallback:** `{'ON' if config.DEMO_MODE else 'OFF'}`\n")

    lines.append("---")
    lines.append("### 📊 Cumulative Incident Metrics")
    lines.append(f"- **Total Crisis Reports Processed:** **{stats['total_reports']}**")
    lines.append(f"- **High & Critical Severity Incidents:** **{stats['high_critical_count']}**\n")

    if stats["by_type"]:
        lines.append("### 🗂️ Incident Distribution by Crisis Category")
        for row in stats["by_type"]:
            lines.append(f"- **{row['crisis_type']}**: {row['count']} reports")
        lines.append("")

    if stats["recent"]:
        lines.append("### 🕒 Recent Emergency Briefings")
        for row in stats["recent"]:
            lines.append(
                f"- **#{row['id']}** — `{row['crisis_type']}` in **{row['location']}** "
                f"(*{row['severity']}*) — {row['created_at']}"
            )

    return "\n".join(lines)


# ---------- Build Gradio Interface ----------

with gr.Blocks(title="CrisisPulse AI — Multi-Agent Crisis Intelligence", theme=gr.themes.Soft(
    primary_hue="indigo", secondary_hue="cyan", neutral_hue="slate",
)) as demo:

    gr.HTML(
        """
        <div class="cp-hero">
          <div class="cp-hero-inner">
            <div class="cp-badge-pulse">🆘</div>
            <div>
              <p class="cp-hero-title">CrisisPulse AI</p>
              <p class="cp-hero-sub">Multi-Agent Crisis Intelligence • Relevance → Extraction → Live Verification → Severity → Summary</p>
              <div class="cp-chip-row">
                <span class="cp-chip groq">⚡ Groq LLM inference</span>
                <span class="cp-chip tavily">🌐 Tavily live verification</span>
                <span class="cp-chip db">🗄️ Neon Postgres</span>
              </div>
            </div>
          </div>
        </div>
        """
    )

    current_analysis_id = gr.State(None)

    with gr.Tab("🚨 Analyze Incident"):
        gr.Markdown("### 📥 Input Emergency Report")
        gr.Markdown("**Quick Load Sample Incidents:**")
        with gr.Row():
            sample_flood = gr.Button("🌊 Flood (Mumbai)", size="sm", elem_classes=["sample-btn"])
            sample_eq = gr.Button("🏚️ Earthquake (Anjar)", size="sm", elem_classes=["sample-btn"])
            sample_fire = gr.Button("🔥 Industrial Fire", size="sm", elem_classes=["sample-btn"])
            sample_cyclone = gr.Button("🌀 Cyclone (Gujarat)", size="sm", elem_classes=["sample-btn"])
            sample_heat = gr.Button("☀️ Heatwave (Rajasthan)", size="sm", elem_classes=["sample-btn"])
            sample_ctrl = gr.Button("☕ Non-Crisis Control", size="sm", elem_classes=["sample-btn"])

        with gr.Row():
            with gr.Column(scale=1, elem_classes=["cp-panel"]):
                report_text = gr.Textbox(
                    label="Crisis Report Text",
                    placeholder="Paste emergency report or news feed text here...",
                    lines=10,
                )
                uploaded_file = gr.File(
                    label="...or upload .txt / .pdf document",
                    file_types=[".txt", ".pdf"],
                    type="filepath",
                )
                analyze_btn = gr.Button("🔍 Run Multi-Agent Pipeline", variant="primary", size="lg", elem_id="cp-run-btn")

            with gr.Column(scale=1, elem_classes=["cp-panel"]):
                result_output = gr.Markdown(
                    value="### ⏳ Awaiting Analysis Output\nPaste or select an emergency report on the left and click **🔍 Run Multi-Agent Pipeline** to view the generated emergency briefing here.",
                    label="Emergency Briefing Result",
                )
                pdf_download = gr.File(label="📄 Download Formatted PDF Briefing", visible=False)
                status_output = gr.Markdown(
                    value="*Agent workflow execution details will appear here after starting pipeline.*",
                    label="Agent Status Workflow",
                )

        sample_flood.click(fn=lambda: SAMPLE_REPORTS["🌊 Flood (Mumbai)"], outputs=report_text)
        sample_eq.click(fn=lambda: SAMPLE_REPORTS["🏚️ Earthquake (Anjar)"], outputs=report_text)
        sample_fire.click(fn=lambda: SAMPLE_REPORTS["🔥 Industrial Fire (Pune)"], outputs=report_text)
        sample_cyclone.click(fn=lambda: SAMPLE_REPORTS["🌀 Cyclone (Gujarat Coast)"], outputs=report_text)
        sample_heat.click(fn=lambda: SAMPLE_REPORTS["☀️ Heatwave (Rajasthan)"], outputs=report_text)
        sample_ctrl.click(fn=lambda: SAMPLE_REPORTS["☕ Non-Crisis Control"], outputs=report_text)

        analyze_btn.click(
            fn=analyze_callback,
            inputs=[report_text, uploaded_file],
            outputs=[result_output, status_output, current_analysis_id, pdf_download],
            show_progress=True,
        )

    with gr.Tab("🗂️ Incident History"):
        gr.Markdown("### 📜 Past Analysis Archives")
        with gr.Row():
            severity_filter = gr.Dropdown(
                choices=["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"], value="ALL",
                label="Filter by Severity Level", interactive=True,
            )
            refresh_btn = gr.Button("🔄 Refresh History", size="sm")

        history_table = gr.Dataframe(
            headers=["ID", "Crisis Type", "Location", "Severity", "Created At"],
            datatype=["number", "str", "str", "str", "str"],
            interactive=False,
        )

        gr.Markdown("### 🔎 Load Detailed Past Briefing")
        with gr.Row():
            analysis_id_input = gr.Number(label="Analysis ID #", precision=0)
            load_btn = gr.Button("Load Briefing", variant="secondary")

        history_result = gr.Markdown()
        history_pdf_download = gr.File(label="📄 Download Formatted PDF Briefing", visible=False)

        severity_filter.change(fn=load_history_callback, inputs=severity_filter, outputs=history_table)
        refresh_btn.click(fn=load_history_callback, inputs=severity_filter, outputs=history_table)
        load_btn.click(fn=load_result_by_id_callback, inputs=analysis_id_input, outputs=[history_result, history_pdf_download])
        demo.load(fn=load_history_callback, inputs=severity_filter, outputs=history_table)

    with gr.Tab("📈 Analytics & Status"):
        gr.Markdown("### 📊 CrisisPulse AI Command Dashboard")
        dashboard_refresh_btn = gr.Button("🔄 Refresh Metrics")
        dashboard_output = gr.Markdown()

        dashboard_refresh_btn.click(fn=load_dashboard_callback, inputs=None, outputs=dashboard_output)
        demo.load(fn=load_dashboard_callback, inputs=None, outputs=dashboard_output)

    with gr.Tab("ℹ️ Setup & About"):
        gr.Markdown(
            """
### 🔑 API Keys
This project uses **only two external APIs** — no Ollama, no local model server:

| Service | Purpose | Get a key |
|---|---|---|
| **Groq** | Ultra-fast LLM inference for all 4 reasoning agents | https://console.groq.com/keys |
| **Tavily** | Live web search for the Verification Agent | https://app.tavily.com |

Add both to your `.env` file (see `.env.example`). If `GROQ_API_KEY` is missing, the app
runs in **Demo Mode** with sample output so you can still explore the UI.

### 🗄️ Database: Neon Postgres (default for deployment)
This app is configured to run on **Neon** so your incident history survives redeploys and
restarts. Create a free project at https://neon.tech, copy your pooled connection string, and
set `DATABASE_URL` in `.env` — tables are created automatically on first run.

Leaving `DATABASE_URL` empty falls back to a local SQLite file for quick offline testing only;
it is **not** recommended once you deploy, since most hosts reset the filesystem on redeploy.
See `README.md` for full setup steps.
            """
        )

    gr.HTML('<div class="cp-footnote">CrisisPulse AI • Groq + Tavily powered • Built with Gradio</div>')


if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=int(os.getenv("PORT", "7860")), css=CUSTOM_CSS, js=CUSTOM_JS)
