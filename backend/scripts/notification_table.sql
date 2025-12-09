-- notification_analyses table for Turso
-- Simple schema - renamed 'references' to avoid SQL reserved word

CREATE TABLE IF NOT EXISTS notification_analyses (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    filename TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    notification_type TEXT,
    region TEXT,
    is_foral INTEGER DEFAULT 0,
    summary TEXT,
    deadlines TEXT,
    reference_links TEXT,
    severity TEXT,
    notification_date TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_notif_user 
ON notification_analyses(user_id, created_at DESC);
