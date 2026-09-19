# 🆘 CrisisPulse AI — Multi-Agent Crisis Intelligence System

A multi-agent crisis intelligence system powered by **Groq + Tavily** APIs with a modern **Gradio** web interface.

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
3. Live Verification Agent (Tavily + Groq) — real-time web search + grounded note
        │
        ▼
4. Severity Agent         (Groq)  — LOW / MEDIUM / HIGH / CRITICAL + reasoning
        │
        ▼
5. Summary & Action Agent (Groq)  — summary, key points, safety actions, alert
        │
        ▼
Stored in DB (SQLite or Neon Postgres) → shown in Gradio UI → downloadable PDF briefing
```

Only two external APIs are used anywhere in this project:

| Service | Role |
|---|---|
| **[Groq](https://console.groq.com/keys)** | Ultra-fast LLM inference for all reasoning agents |
| **[Tavily](https://app.tavily.com)** | Live web search to verify reports against current real news |

*No Ollama or local model server required.*

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/SHIVANGI-2006/CrisisPulse-AI.git
cd CrisisPulse-AI/CrisisPulse-AI
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
Add your API keys to `.env`:
```env
GROQ_API_KEY="your_groq_api_key"
TAVILY_API_KEY="your_tavily_api_key"
DATABASE_URL="postgresql://user:password@ep-xxxx.neon.tech/neondb?sslmode=require"
```

### 4. Run the application
```bash
python app.py
```
Open **`http://localhost:7860`** in your browser!

## Project Structure

```
CrisisPulse-AI/
├── CrisisPulse-AI/
│   ├── app.py                     # Gradio UI & app entry point
│   ├── config.py                  # Configuration loader
│   ├── requirements.txt           # Python dependencies
│   ├── .env.example               # Template for environment variables
│   ├── agents/
│   │   ├── relevance_agent.py     # Agent 1 (Relevance filtering)
│   │   ├── extraction_agent.py    # Agent 2 (Information extraction)
│   │   ├── verification_agent.py  # Agent 3 (Tavily live web verification)
│   │   ├── severity_agent.py      # Agent 4 (Severity classification)
│   │   ├── summary_agent.py       # Agent 5 (Summary & safety actions)
│   │   └── orchestrator.py        # Sequenced pipeline controller
│   ├── services/
│   │   ├── llm_service.py         # Groq API wrapper with model fallback
│   │   ├── tavily_service.py      # Tavily search API wrapper
│   │   ├── database_service.py    # SQLAlchemy database (Neon / SQLite)
│   │   ├── pdf_service.py         # Formatted PDF export generator
│   │   └── demo_data.py           # Demo dataset
│   ├── utils/
│   │   ├── json_parser.py         # Robust JSON extractor
│   │   └── text_utils.py          # Cleaning & IST formatting
│   └── database/
│       └── schema.sql             # SQL Schema reference
└── README.md
```
