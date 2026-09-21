# 🆘 CrisisPulse AI — Multi-Agent Crisis Intelligence System

A rebuild of the original Crisis Summarizer, ported off Ollama onto a
**Groq + Tavily** backend with a redesigned **Gradio** front end.

## Architecture

```
User report (text / .txt / .pdf)
        │
        ▼
1. Relevance Agent        (Groq)  — is this really a crisis? clean the text
        │
        ▼
2. Extraction Agent       (Groq)  — structured facts (type, location, casualties...)
        │
        ▼
3. Live Verification Agent (Tavily + Groq) — real-time web search + grounded note  ★ NEW
        │
        ▼
4. Severity Agent         (Groq)  — LOW / MEDIUM / HIGH / CRITICAL + reasoning
        │
        ▼
5. Summary & Action Agent (Groq)  — summary, key points, safety actions, alert
        │
        ▼
Stored in DB (SQLite or Neon) → shown in Gradio UI → downloadable PDF briefing
```

Only two external APIs are used anywhere in this project:

| Service | Role |
|---|---|
| **[Groq](https://console.groq.com/keys)** | LLM inference for all 4 reasoning agents (fast + cheap, JSON mode for reliable structured output) |
| **[Tavily](https://app.tavily.com)** | Live web search that lets the Verification Agent check a report against real current news |

No Ollama, no local model server, no other LLM provider.

## Quick start (Neon-first, since you're deploying this)

**Step 1 — create your Neon database (do this first):**
1. Go to https://neon.tech and create a free account/project.
2. In your project, open **Connection Details**.
3. Turn **Pooled connection** ON (recommended — Gradio can spin up multiple
   workers) and copy the **Connection string**. It looks like:
   `postgresql://user:password@ep-xxxx-pooler.region.neon.tech/neondb?sslmode=require`

**Step 2 — configure the app:**
```bash
pip install -r requirements.txt
cp .env.example .env
```
Edit `.env` and paste your connection string into `DATABASE_URL`, plus your
`GROQ_API_KEY` (and optionally `TAVILY_API_KEY`):
```bash
DATABASE_URL=postgresql://user:password@ep-xxxx-pooler.region.neon.tech/neondb?sslmode=require
GROQ_API_KEY=your_groq_key
TAVILY_API_KEY=your_tavily_key
```

**Step 3 — run it:**
```bash
python app.py
```
On first run, `services/database_service.py` connects to Neon and
auto-creates the `crisis_reports` / `analysis_results` tables — no manual
SQL needed. The app opens at `http://localhost:7860`.

Without a `GROQ_API_KEY` set, the app runs in **Demo Mode**
(`DEMO_MODE=true` by default) so you can explore the UI with sample output.
If `DATABASE_URL` is left empty it silently falls back to a local SQLite
file for convenience, but you'll see a warning in the logs — **fill in
`DATABASE_URL` before you deploy** so incident history survives restarts.

## Why Neon by default

This project is set up to deploy, so Neon (not local SQLite) is the intended
production database:
- **Persistence across redeploys** — most hosts (HF Spaces, Render, Railway,
  Fly.io, etc.) reset the filesystem on redeploy; a local SQLite file would
  lose all incident history. Neon is a separate, always-on database.
- **Concurrent access** — if more than one worker/instance serves the app,
  or more than one person uses it, Postgres handles concurrent writes
  properly where a single SQLite file does not.
- **Scales without touching code** — as report volume grows, Neon's
  managed Postgres scales with it; SQLite does not.
- **Free to start, zero server ops** — no database server to install,
  patch, or back up yourself.

The local SQLite fallback (`DATABASE_URL` empty) still exists purely for
quick offline testing on your own machine — it is not meant for deployment.
Both paths run through the exact same SQLAlchemy code in
`services/database_service.py`, so there's nothing else to change.

## Project structure

```
CrisisPulse-AI/
├── app.py                     # Gradio UI (custom CSS/JS, 3 tabs + about)
├── config.py                  # Env-driven configuration
├── requirements.txt
├── .env.example
├── agents/
│   ├── relevance_agent.py     # Agent 1 (Groq)
│   ├── extraction_agent.py    # Agent 2 (Groq)
│   ├── verification_agent.py  # Agent 3 (Tavily + Groq)  ★ NEW
│   ├── severity_agent.py      # Agent 4 (Groq)
│   ├── summary_agent.py       # Agent 5 (Groq)
│   └── orchestrator.py        # Runs the 5-agent pipeline in order
├── services/
│   ├── llm_service.py         # Groq client wrapper
│   ├── tavily_service.py      # Tavily client wrapper       ★ NEW
│   ├── database_service.py    # SQLAlchemy: SQLite or Neon
│   ├── pdf_service.py         # ReportLab PDF export
│   └── demo_data.py           # Offline demo fallback
├── utils/
│   ├── json_parser.py         # Robust JSON extraction from LLM output
│   └── text_utils.py          # Cleaning / validation / IST timestamps
└── database/
    └── schema.sql             # Reference schema (auto-created by the app)
```

## Notes on the new Verification Agent

The original project's pipeline stopped at severity + summary using only
information present in the submitted text. This build adds a **Live
Verification Agent** between extraction and severity: it searches Tavily for
recent news matching the extracted crisis type + location, then asks Groq to
write a short, source-grounded note on whether the report is corroborated,
along with clickable source links shown in the UI and included in the
exported PDF. If `TAVILY_API_KEY` isn't set, this step is skipped gracefully
and the rest of the pipeline still runs normally.
