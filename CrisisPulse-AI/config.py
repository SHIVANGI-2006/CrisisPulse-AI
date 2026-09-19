"""
config.py
Centralized configuration loaded from environment variables (.env).
Nothing sensitive is hardcoded here.

This build is powered ONLY by:
  - Groq   -> fast LLM inference for all reasoning agents
  - Tavily -> live web search for the Verification Agent
No Ollama / local model server is used anywhere in this project.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ---------------- Groq (LLM) ----------------
    GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
    # Good default: fast + strong reasoning. Override in .env if you like.
    GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
    GROQ_TIMEOUT = int(os.getenv("GROQ_TIMEOUT", "60"))

    # ---------------- Tavily (live web verification) ----------------
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "").strip()
    ENABLE_LIVE_VERIFICATION = os.getenv("ENABLE_LIVE_VERIFICATION", "true").lower() == "true"

    # ---------------- Database (Neon Postgres by default) ----------------
    # Set DATABASE_URL to your Neon connection string before deploying, so
    # incident history/analytics persist across restarts and redeploys.
    # If left empty, the app falls back to a local SQLite file - fine for a
    # quick local test, but not recommended once you deploy. See README.
    DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
    LOCAL_DB_PATH = os.getenv("LOCAL_DB_PATH", "database/crisis.db")

    # Demo mode: if no Groq key is configured, the app can still be explored
    # using canned example output instead of hard failing.
    DEMO_MODE = os.getenv("DEMO_MODE", "true").lower() == "true"

    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")

    # ---------------- Input validation ----------------
    MAX_REPORT_CHARS = 8000
    MIN_REPORT_CHARS = 15
    ALLOWED_EXTENSIONS = {"txt", "pdf"}


config = Config()
