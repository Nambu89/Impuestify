-- autonomous_quotas table for Turso
-- Stores the 15 income brackets and their corresponding quotas for 2025+

CREATE TABLE IF NOT EXISTS autonomous_quotas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    year INTEGER NOT NULL,
    tramo_number INTEGER NOT NULL,
    rendimientos_netos_min REAL NOT NULL,  -- Minimum monthly net income (€)
    rendimientos_netos_max REAL,           -- Maximum monthly net income (€), NULL for last tramo
    base_cotizacion_min REAL NOT NULL,     -- Minimum contribution base (€)
    base_cotizacion_max REAL NOT NULL,     -- Maximum contribution base (€)
    cuota_min REAL NOT NULL,               -- Minimum monthly quota (€)
    cuota_max REAL NOT NULL,               -- Maximum monthly quota (€)
    region TEXT DEFAULT 'general',         -- 'general', 'ceuta', 'melilla' (for bonuses)
    bonificacion_percent REAL DEFAULT 0,   -- Bonus percentage (e.g., 50 for Ceuta/Melilla)
    cuota_min_bonificada REAL,             -- Minimum quota after bonus
    cuota_max_bonificada REAL,             -- Maximum quota after bonus
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(year, tramo_number, region)
);

-- Index for fast lookups by year and income range
CREATE INDEX IF NOT EXISTS idx_quota_year_income 
ON autonomous_quotas(year, rendimientos_netos_min, rendimientos_netos_max);

-- Index for region-specific queries
CREATE INDEX IF NOT EXISTS idx_quota_region 
ON autonomous_quotas(year, region);
