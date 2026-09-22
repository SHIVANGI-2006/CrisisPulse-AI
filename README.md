# 🆘 CrisisPulse AI — Multi-Agent Crisis Intelligence System

CrisisPulse AI is an emergency crisis intelligence and briefing system built with **Python**, **Gradio**, **Groq LLM inference**, **Tavily live web verification**, **SQLAlchemy**, and **ReportLab PDF generation**.

---

## 🏗️ Architecture

```text
User Report (text / .txt / .pdf)
         │
         ▼
1. Relevance Agent        (Groq)  — Filters irrelevant text & checks crisis relevance
         │
         ▼
2. Extraction Agent       (Groq)  — Extracts structured facts (type, location, casualties...)
         │
         ▼
3. Live Verification Agent (Tavily + Groq) — Real-time news search & grounded verification
         │
         ▼
4. Severity Agent         (Groq)  — Assigns LOW / MEDIUM / HIGH / CRITICAL with rationale
         │
         ▼
5. Summary & Action Agent (Groq)  — Synthesizes executive briefing & safety actions
         │
         ▼
Persistence (SQLite / Neon Postgres) ──► Gradio Web Interface ──► Downloadable PDF Briefing
```

---

## 🛠️ Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| **LLM Reasoning** | Groq API (`openai/gpt-oss-120b`, `llama-3.3-70b-versatile`) | Fast, structured multi-agent reasoning |
| **Live Verification** | Tavily Web Search API | Real-time news grounding and source citation |
| **User Interface** | Gradio (v4.44+) | Dark glassmorphic command dashboard |
| **Database** | SQLAlchemy (SQLite / Neon PostgreSQL) | Persistent report history & analytics |
| **PDF Briefings** | ReportLab | Export formatted PDF crisis briefings |
| **Document Parsing** | PyPDF / standard I/O | `.txt` and `.pdf` emergency document ingestion |

---

## 🚀 Quick Start (Local Setup)

### 1. Clone the repository
```bash
git clone https://github.com/SHIVANGI-2006/CrisisPulse-AI.git
cd CrisisPulse-AI
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Populate `.env` with your API keys:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
TAVILY_API_KEY=tvly_your_tavily_api_key_here
DATABASE_URL=postgresql://user:password@ep-xxxx.neon.tech/neondb?sslmode=require
GROQ_MODEL=openai/gpt-oss-120b
ENABLE_LIVE_VERIFICATION=true
DEMO_MODE=false
```

### 4. Run the application
```bash
python app.py
```
Open **`http://localhost:7860`** in your browser.

---

## ☁️ Render Deployment Guide

### Deployment Settings on Render:
- **Environment:** Python 3
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python app.py`

### Environment Variables on Render:
| Variable | Value / Description | Sync |
|---|---|---|
| `GROQ_API_KEY` | Your Groq API key (`gsk_...`) | Secret (`sync: false`) |
| `TAVILY_API_KEY` | Your Tavily API key (`tvly-...`) | Secret (`sync: false`) |
| `DATABASE_URL` | Neon Postgres pooled connection string | Secret (`sync: false`) |
| `GROQ_MODEL` | `openai/gpt-oss-120b` | `openai/gpt-oss-120b` |
| `ENABLE_LIVE_VERIFICATION` | `true` | `true` |
| `DEMO_MODE` | `false` | `false` |

---

## 🛡️ Robustness & Fallback Behavior

1. **Groq JSON Validation Recovery:** If Groq raises `json_validate_failed` or `400` error during JSON mode generation, `LLMService` automatically retries without `response_format` constraint and extracts structured data using `utils/json_parser.py`.
2. **Model Fallback:** If the configured model is unavailable, `LLMService` automatically cycles through candidate models (`openai/gpt-oss-120b` → `llama-3.3-70b-versatile` → `llama-3.1-8b-instant`).
3. **Database Fallback:** If `DATABASE_URL` is empty or PostgreSQL is unreachable, the database service automatically falls back to local SQLite (`database/crisis.db`).
4. **Tavily Fallback:** If `TAVILY_API_KEY` is missing or Tavily fails, live verification is marked as unavailable while the rest of the multi-agent pipeline completes normally.
5. **Demo Mode:** If `GROQ_API_KEY` is not set, the app runs in **Demo Mode**, displaying sample incident analysis without crashing.
