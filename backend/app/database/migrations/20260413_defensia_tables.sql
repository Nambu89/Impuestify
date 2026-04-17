-- DefensIA — 7 tablas base
-- Spec: plans/2026-04-13-defensia-design.md §7.4

CREATE TABLE IF NOT EXISTS defensia_expedientes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    nombre TEXT NOT NULL,
    tributo TEXT NOT NULL CHECK (tributo IN ('IRPF','IVA','ISD','ITP','PLUSVALIA')),
    ccaa TEXT NOT NULL,
    tipo_procedimiento_declarado TEXT NOT NULL,
    fase_detectada TEXT,
    fase_confianza REAL,
    estado TEXT NOT NULL DEFAULT 'borrador'
        CHECK (estado IN ('borrador','en_analisis','dictamen_listo','archivado')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_defensia_exp_user
    ON defensia_expedientes(user_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS defensia_documentos (
    id TEXT PRIMARY KEY,
    expediente_id TEXT NOT NULL,
    nombre_original TEXT NOT NULL,
    ruta_almacenada TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    tamano_bytes INTEGER NOT NULL,
    hash_sha256 TEXT NOT NULL,
    tipo_documento TEXT,
    clasificacion_confianza REAL,
    fecha_acto TEXT,
    datos_estructurados_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (expediente_id) REFERENCES defensia_expedientes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_defensia_docs_exp
    ON defensia_documentos(expediente_id, fecha_acto);

CREATE TABLE IF NOT EXISTS defensia_briefs (
    id TEXT PRIMARY KEY,
    expediente_id TEXT NOT NULL,
    texto TEXT NOT NULL,
    chat_history_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (expediente_id) REFERENCES defensia_expedientes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS defensia_dictamenes (
    id TEXT PRIMARY KEY,
    expediente_id TEXT NOT NULL,
    brief_id TEXT,
    fase_detectada TEXT NOT NULL,
    argumentos_json TEXT NOT NULL,
    resumen_caso TEXT NOT NULL,
    created_at TEXT NOT NULL,
    modelo_llm TEXT NOT NULL DEFAULT 'gpt-5-mini',
    tokens_consumidos INTEGER,
    FOREIGN KEY (expediente_id) REFERENCES defensia_expedientes(id) ON DELETE CASCADE,
    FOREIGN KEY (brief_id) REFERENCES defensia_briefs(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS defensia_escritos (
    id TEXT PRIMARY KEY,
    expediente_id TEXT NOT NULL,
    dictamen_id TEXT NOT NULL,
    tipo_escrito TEXT NOT NULL,
    contenido_markdown TEXT NOT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    editado_por_usuario INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (expediente_id) REFERENCES defensia_expedientes(id) ON DELETE CASCADE,
    FOREIGN KEY (dictamen_id) REFERENCES defensia_dictamenes(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS defensia_cuotas_mensuales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    ano_mes TEXT NOT NULL,
    expedientes_creados INTEGER NOT NULL DEFAULT 0,
    UNIQUE(user_id, ano_mes),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS defensia_rag_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    expediente_id TEXT NOT NULL,
    regla_id TEXT NOT NULL,
    soportado INTEGER NOT NULL,
    confianza REAL,
    razonamiento TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (expediente_id) REFERENCES defensia_expedientes(id) ON DELETE CASCADE
);
