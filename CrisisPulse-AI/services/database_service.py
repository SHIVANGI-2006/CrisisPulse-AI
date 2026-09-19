"""
services/database_service.py

Handles all database interactions for CrisisPulse AI.

Backed by SQLAlchemy so the SAME code works against:
  1. Local SQLite  (default - zero setup, file on disk)
  2. Neon Postgres (set DATABASE_URL in .env - hosted, persistent, shareable)

See README.md for a full comparison of when to pick which.
"""

import json
import logging
import os

from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Boolean, ForeignKey
)
from sqlalchemy.orm import declarative_base, sessionmaker

from config import config
from utils.text_utils import get_ist_now_str, format_to_ist

logger = logging.getLogger("crisis_agent.database")

Base = declarative_base()


class CrisisReport(Base):
    __tablename__ = "crisis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_text = Column(Text, nullable=False)
    source = Column(String(255), default="manual")
    created_at = Column(String(64))


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_id = Column(Integer, ForeignKey("crisis_reports.id"), nullable=False)

    crisis_type = Column(String(64))
    location = Column(String(255))
    date_time = Column(String(255))
    severity = Column(String(32))
    severity_reason = Column(Text)
    affected_people = Column(Text)
    casualties = Column(Text)
    infrastructure_damage = Column(Text)
    transport_disruption = Column(Text)

    key_points = Column(Text)               # JSON-encoded list
    summary = Column(Text)
    safety_recommendations = Column(Text)    # JSON-encoded list
    alert_message = Column(Text)

    # Live verification (Tavily) fields
    corroborated = Column(String(16))        # "true" | "false" | "unknown"
    verification_note = Column(Text)
    live_sources = Column(Text)              # JSON-encoded list of {title,url}

    demo_mode = Column(Boolean, default=False)
    created_at = Column(String(64))


class DatabaseService:
    def __init__(self, database_url: str = None, local_path: str = None):
        db_url = (database_url or config.DATABASE_URL or "").strip()

        connected = False
        if db_url:
            # Normalize Neon / Heroku-style postgres:// URLs for SQLAlchemy + psycopg2
            if db_url.startswith("postgres://"):
                normalized_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
            elif db_url.startswith("postgresql://") and "+psycopg2" not in db_url:
                normalized_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
            else:
                normalized_url = db_url

            connect_args = {"sslmode": "require"} if "sslmode" not in normalized_url else {}
            try:
                self.engine = create_engine(normalized_url, connect_args=connect_args, pool_pre_ping=True)
                Base.metadata.create_all(self.engine)
                self.Session = sessionmaker(bind=self.engine)
                self.backend_label = "Neon / Postgres (hosted)"
                connected = True
                logger.info("Database initialized. Backend: %s", self.backend_label)
            except Exception as exc:
                logger.warning("Failed to connect to Neon database (%s). Falling back to local SQLite.", exc)

        if not connected:
            path = local_path or config.LOCAL_DB_PATH
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            db_url = f"sqlite:///{path}"
            self.backend_label = "SQLite (local fallback — set DATABASE_URL for Neon)"
            connect_args = {"check_same_thread": False}
            self.engine = create_engine(db_url, connect_args=connect_args, pool_pre_ping=True)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("Database initialized. Backend: %s", self.backend_label)

    # ---------- WRITE OPERATIONS ----------

    def save_report(self, report_text: str, source: str = "manual") -> int:
        session = self.Session()
        try:
            row = CrisisReport(
                report_text=report_text, source=source, created_at=get_ist_now_str()
            )
            session.add(row)
            session.commit()
            return row.id
        except Exception as exc:
            session.rollback()
            logger.error("Failed to save report: %s", exc)
            raise
        finally:
            session.close()

    def save_analysis(self, report_id: int, result: dict, demo_mode: bool = False) -> int:
        session = self.Session()
        try:
            row = AnalysisResult(
                report_id=report_id,
                crisis_type=result.get("crisis_type", "Other"),
                location=result.get("location", "Unknown"),
                date_time=result.get("date_time", "Not specified"),
                severity=result.get("severity", "LOW"),
                severity_reason=result.get("severity_reason", ""),
                affected_people=result.get("affected_people", "Unknown"),
                casualties=result.get("casualties", "None reported"),
                infrastructure_damage=result.get("infrastructure_damage", "None reported"),
                transport_disruption=result.get("transport_disruption", "None reported"),
                key_points=json.dumps(result.get("key_points", [])),
                summary=result.get("summary", ""),
                safety_recommendations=json.dumps(result.get("safety_recommendations", [])),
                alert_message=result.get("alert_message", ""),
                corroborated=str(result.get("corroborated", "unknown")),
                verification_note=result.get("verification_note", ""),
                live_sources=json.dumps(result.get("live_sources", [])),
                demo_mode=bool(demo_mode),
                created_at=get_ist_now_str(),
            )
            session.add(row)
            session.commit()
            return row.id
        except Exception as exc:
            session.rollback()
            logger.error("Failed to save analysis: %s", exc)
            raise
        finally:
            session.close()

    # ---------- READ OPERATIONS ----------

    def get_history(self, limit: int = 200):
        session = self.Session()
        try:
            rows = (
                session.query(AnalysisResult, CrisisReport.report_text)
                .join(CrisisReport, AnalysisResult.report_id == CrisisReport.id)
                .order_by(AnalysisResult.id.desc())
                .limit(limit)
                .all()
            )
            results = []
            for a, report_text in rows:
                results.append({
                    "id": a.id,
                    "report_id": a.report_id,
                    "crisis_type": a.crisis_type,
                    "location": a.location,
                    "severity": a.severity,
                    "created_at": format_to_ist(a.created_at),
                    "report_text": report_text,
                })
            return results
        except Exception as exc:
            logger.error("Failed to fetch history: %s", exc)
            return []
        finally:
            session.close()

    def get_result_by_id(self, analysis_id: int):
        session = self.Session()
        try:
            row = (
                session.query(AnalysisResult, CrisisReport.report_text)
                .join(CrisisReport, AnalysisResult.report_id == CrisisReport.id)
                .filter(AnalysisResult.id == analysis_id)
                .first()
            )
            if not row:
                return None
            a, report_text = row
            return {
                "id": a.id,
                "report_id": a.report_id,
                "crisis_type": a.crisis_type,
                "location": a.location,
                "date_time": a.date_time,
                "severity": a.severity,
                "severity_reason": a.severity_reason,
                "affected_people": a.affected_people,
                "casualties": a.casualties,
                "infrastructure_damage": a.infrastructure_damage,
                "transport_disruption": a.transport_disruption,
                "key_points": json.loads(a.key_points or "[]"),
                "summary": a.summary,
                "safety_recommendations": json.loads(a.safety_recommendations or "[]"),
                "alert_message": a.alert_message,
                "corroborated": a.corroborated,
                "verification_note": a.verification_note,
                "live_sources": json.loads(a.live_sources or "[]"),
                "demo_mode": a.demo_mode,
                "created_at": format_to_ist(a.created_at),
                "report_text": report_text,
            }
        except Exception as exc:
            logger.error("Failed to fetch result %s: %s", analysis_id, exc)
            return None
        finally:
            session.close()

    def get_dashboard_stats(self):
        session = self.Session()
        try:
            total = session.query(AnalysisResult).count()
            high_critical = (
                session.query(AnalysisResult)
                .filter(AnalysisResult.severity.in_(["HIGH", "CRITICAL"]))
                .count()
            )

            by_type_rows = (
                session.query(AnalysisResult.crisis_type, AnalysisResult.id)
                .all()
            )
            by_type_counts = {}
            for crisis_type, _ in by_type_rows:
                key = crisis_type or "Other"
                by_type_counts[key] = by_type_counts.get(key, 0) + 1
            by_type = [
                {"crisis_type": k, "count": v}
                for k, v in sorted(by_type_counts.items(), key=lambda kv: -kv[1])
            ]

            recent_rows = (
                session.query(AnalysisResult)
                .order_by(AnalysisResult.id.desc())
                .limit(5)
                .all()
            )
            recent = [
                {
                    "id": r.id,
                    "crisis_type": r.crisis_type,
                    "location": r.location,
                    "severity": r.severity,
                    "created_at": format_to_ist(r.created_at),
                }
                for r in recent_rows
            ]

            return {
                "total_reports": total,
                "high_critical_count": high_critical,
                "by_type": by_type,
                "recent": recent,
                "backend_label": self.backend_label,
            }
        except Exception as exc:
            logger.error("Failed to fetch dashboard stats: %s", exc)
            return {
                "total_reports": 0,
                "high_critical_count": 0,
                "by_type": [],
                "recent": [],
                "backend_label": self.backend_label,
            }
        finally:
            session.close()
