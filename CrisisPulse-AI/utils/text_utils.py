"""
utils/text_utils.py
Small helper functions for cleaning/validating raw report text and for
formatting timestamps consistently in IST across the app.
"""

import re
from datetime import datetime, timezone, timedelta

from config import config

IST = timezone(timedelta(hours=5, minutes=30))


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def validate_report_text(text: str):
    cleaned = clean_text(text)
    if not cleaned:
        return False, "Report text cannot be empty."
    if len(cleaned) < config.MIN_REPORT_CHARS:
        return False, f"Report text is too short (minimum {config.MIN_REPORT_CHARS} characters)."
    if len(cleaned) > config.MAX_REPORT_CHARS:
        return False, f"Report text is too long (maximum {config.MAX_REPORT_CHARS} characters)."
    return True, None


def split_multiple_reports(raw_text: str):
    if not raw_text:
        return []
    parts = re.split(r"\n\s*(?:---+|\n)\s*\n?", raw_text.strip())
    return [clean_text(p) for p in parts if clean_text(p)]


def allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in config.ALLOWED_EXTENSIONS
    )


def get_ist_now_str() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def format_to_ist(dt_str: str) -> str:
    if not dt_str:
        return ""
    if "IST" in str(dt_str):
        return str(dt_str)
    try:
        dt_str_clean = str(dt_str).replace("T", " ").split(".")[0]
        dt_utc = datetime.strptime(dt_str_clean, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
        dt_ist = dt_utc.astimezone(IST)
        return dt_ist.strftime("%Y-%m-%d %H:%M:%S IST")
    except Exception:
        return str(dt_str)
