-- schema.sql
-- Reference schema for CrisisPulse AI.
-- NOTE: the app auto-creates these tables via SQLAlchemy on startup
-- (works identically on SQLite and Postgres/Neon). This file is kept for
-- reference / manual inspection only.

CREATE TABLE IF NOT EXISTS crisis_reports (
    id SERIAL PRIMARY KEY,
    report_text TEXT NOT NULL,
    source VARCHAR(255) DEFAULT 'manual',
    created_at VARCHAR(64)
);

CREATE TABLE IF NOT EXISTS analysis_results (
    id SERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES crisis_reports(id),
    crisis_type VARCHAR(64),
    location VARCHAR(255),
    date_time VARCHAR(255),
    severity VARCHAR(32),
    severity_reason TEXT,
    affected_people TEXT,
    casualties TEXT,
    infrastructure_damage TEXT,
    transport_disruption TEXT,
    key_points TEXT,               -- JSON-encoded list
    summary TEXT,
    safety_recommendations TEXT,   -- JSON-encoded list
    alert_message TEXT,
    corroborated VARCHAR(16),      -- 'true' | 'false' | 'unknown'
    verification_note TEXT,
    live_sources TEXT,             -- JSON-encoded list of {title,url}
    demo_mode BOOLEAN DEFAULT FALSE,
    created_at VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_analysis_report_id ON analysis_results (report_id);
CREATE INDEX IF NOT EXISTS idx_analysis_severity ON analysis_results (severity);
