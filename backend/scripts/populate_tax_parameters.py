"""
Populate tax_parameters table with fiscal data for IRPF simulation.

All tax rates, thresholds, and amounts are stored in the database
so they can be updated without code changes.

Data sources:
- LIRPF (Ley 35/2006 del IRPF) arts. 17-20, 22-23, 57-61, 63-66
- LIVA (Ley 37/1992 del IVA) arts. 90-91
- LGSS (cotizaciones SS empleado)
- Normativa autonómica (MPYF overrides por CCAA)
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient


# =============================================================================
# MPYF — Mínimo Personal y Familiar (LIRPF arts. 57-61)
# =============================================================================

MPYF_ESTATAL = {
    "contribuyente": (5550, "LIRPF art.57.1"),
    "contribuyente_65": (6700, "LIRPF art.57.2"),
    "contribuyente_75": (8100, "LIRPF art.57.2"),
    "descendiente_1": (2400, "LIRPF art.58.1"),
    "descendiente_2": (2700, "LIRPF art.58.1"),
    "descendiente_3": (4000, "LIRPF art.58.1"),
    "descendiente_4_plus": (4500, "LIRPF art.58.1"),
    "descendiente_menor_3": (2800, "LIRPF art.58.2"),
    "ascendiente_65": (1150, "LIRPF art.59"),
    "ascendiente_75": (2550, "LIRPF art.59"),
    "discapacidad_33_65": (3000, "LIRPF art.60.1"),
    "discapacidad_65_plus": (9000, "LIRPF art.60.1"),
    "gastos_asistencia": (3000, "LIRPF art.60.2"),
}

# CCAAs con mínimos autonómicos diferentes al estatal (2024).
# Solo incluir las que difieren; el resto usa Estatal por defecto.
# Fuente: Estatal-TributacionAutonomica_Medidas2025_CapI.pdf y normativa autonómica.
MPYF_CCAA_OVERRIDES = {
    "Comunitat Valenciana": {
        # Ley 13/1997 de la Generalitat Valenciana, art. 4
        "contribuyente": (6105, "Ley 13/1997 GV art.4.uno"),
        "contribuyente_65": (6705, "Ley 13/1997 GV art.4.uno"),
        "contribuyente_75": (8505, "Ley 13/1997 GV art.4.uno"),
        "descendiente_1": (2400, "Ley 13/1997 GV art.4.dos"),
        "descendiente_2": (2700, "Ley 13/1997 GV art.4.dos"),
        "descendiente_3": (4400, "Ley 13/1997 GV art.4.dos"),
        "descendiente_4_plus": (4950, "Ley 13/1997 GV art.4.dos"),
        "descendiente_menor_3": (2800, "Ley 13/1997 GV art.4.dos"),
    },
    # NOTA: Otras CCAAs que pueden tener overrides en años futuros
    # se añaden aquí. El sistema usa fallback a Estatal automáticamente.
}


# =============================================================================
# RENDIMIENTOS DEL TRABAJO (LIRPF arts. 17-20)
# =============================================================================

TRABAJO_PARAMS = {
    "otros_gastos": (2000, "LIRPF art.19.2.f"),
    "reduccion_max": (6498, "LIRPF art.20.1"),
    "reduccion_rend_min": (14852, "LIRPF art.20.1 — umbral inferior"),
    "reduccion_rend_max": (19747.5, "LIRPF art.20.1 — umbral superior"),
    "cuotas_colegio_max": (500, "LIRPF art.19.2.d"),
    "defensa_juridica_max": (300, "LIRPF art.19.2.e"),
    "ss_empleado_pct": (6.35, "LGSS — contingencias comunes 4.70 + desempleo 1.55 + FP 0.10"),
}


# =============================================================================
# CAPITAL INMOBILIARIO (LIRPF arts. 22-23)
# =============================================================================

INMUEBLES_PARAMS = {
    "reduccion_alquiler_vivienda": (60, "LIRPF art.23.2 — reducción alquiler vivienda habitual"),
    "amortizacion_pct": (3, "LIRPF art.23.1.b — amortización inmuebles"),
}


# =============================================================================
# IVA (LIVA arts. 90-91)
# =============================================================================

IVA_PARAMS = {
    "tipo_general": (21, "LIVA art.90"),
    "tipo_reducido": (10, "LIVA art.91.uno"),
    "tipo_superreducido": (4, "LIVA art.91.dos"),
}


# =============================================================================
# TARIFA DEL AHORRO (LIRPF art.66)
# Formato: (tramo_num, base_hasta, cuota_integra, resto_base, tipo_aplicable)
# =============================================================================

# Escala estatal del ahorro 2024 (LIRPF art.66.1)
AHORRO_ESTATAL_2024 = [
    (1, 6000, 0, 6000, 9.5),
    (2, 50000, 570, 44000, 10.5),
    (3, 200000, 5190, 150000, 11.5),
    (4, 300000, 22440, 100000, 13.5),
    (5, 999999, 35940, 699999, 14),
]

# Escala autonómica del ahorro 2024 (LIRPF art.76)
# La mayoría de CCAAs de régimen común usan la escala complementaria estándar.
# CCAAs que han aprobado escala propia del ahorro se añaden por separado.
AHORRO_AUTONOMICO_2024 = [
    (1, 6000, 0, 6000, 9.5),
    (2, 50000, 570, 44000, 10.5),
    (3, 200000, 5190, 150000, 11.5),
    (4, 300000, 22440, 100000, 13.5),
    (5, 999999, 35940, 699999, 14),
]


async def populate():
    """Populate tax_parameters and ahorro scales."""
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")

    if not turso_url or not turso_token:
        print("❌ Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN")
        return

    db = TursoClient(turso_url, turso_token)
    await db.connect()
    print("✅ Connected to Turso\n")

    year = 2024

    # Ensure table exists
    await db.execute("""
        CREATE TABLE IF NOT EXISTS tax_parameters (
            id TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            param_key TEXT NOT NULL,
            year INTEGER NOT NULL,
            jurisdiction TEXT NOT NULL DEFAULT 'Estatal',
            value REAL NOT NULL,
            description TEXT,
            legal_ref TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(category, param_key, year, jurisdiction)
        )
    """)
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_tax_params_lookup "
        "ON tax_parameters(category, year, jurisdiction)"
    )

    # Clear existing data for this year
    print(f"🧹 Clearing existing {year} tax_parameters data...")
    await db.execute("DELETE FROM tax_parameters WHERE year = ?", [year])

    inserted = 0

    # --- MPYF Estatal ---
    print("\n📊 Inserting MPYF Estatal...")
    for key, (value, ref) in MPYF_ESTATAL.items():
        await db.execute(
            "INSERT INTO tax_parameters (id, category, param_key, year, jurisdiction, value, legal_ref) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), "mpyf", key, year, "Estatal", value, ref]
        )
        inserted += 1
    print(f"  ✓ {len(MPYF_ESTATAL)} parámetros MPYF estatal")

    # --- MPYF CCAA overrides ---
    for ccaa, overrides in MPYF_CCAA_OVERRIDES.items():
        print(f"\n📊 Inserting MPYF overrides for {ccaa}...")
        for key, (value, ref) in overrides.items():
            await db.execute(
                "INSERT INTO tax_parameters (id, category, param_key, year, jurisdiction, value, legal_ref) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                [str(uuid.uuid4()), "mpyf", key, year, ccaa, value, ref]
            )
            inserted += 1
        print(f"  ✓ {len(overrides)} overrides para {ccaa}")

    # --- Trabajo ---
    print("\n📊 Inserting rendimientos del trabajo params...")
    for key, (value, ref) in TRABAJO_PARAMS.items():
        await db.execute(
            "INSERT INTO tax_parameters (id, category, param_key, year, jurisdiction, value, legal_ref) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), "trabajo", key, year, "Estatal", value, ref]
        )
        inserted += 1
    print(f"  ✓ {len(TRABAJO_PARAMS)} parámetros trabajo")

    # --- Inmuebles ---
    print("\n📊 Inserting capital inmobiliario params...")
    for key, (value, ref) in INMUEBLES_PARAMS.items():
        await db.execute(
            "INSERT INTO tax_parameters (id, category, param_key, year, jurisdiction, value, legal_ref) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), "inmuebles", key, year, "Estatal", value, ref]
        )
        inserted += 1
    print(f"  ✓ {len(INMUEBLES_PARAMS)} parámetros inmuebles")

    # --- IVA ---
    print("\n📊 Inserting IVA rates...")
    for key, (value, ref) in IVA_PARAMS.items():
        await db.execute(
            "INSERT INTO tax_parameters (id, category, param_key, year, jurisdiction, value, legal_ref) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), "iva", key, year, "Estatal", value, ref]
        )
        inserted += 1
    print(f"  ✓ {len(IVA_PARAMS)} parámetros IVA")

    # --- Tarifa del Ahorro ---
    print("\n📊 Inserting tarifa del ahorro (irpf_scales)...")
    # Clear existing ahorro scales
    await db.execute(
        "DELETE FROM irpf_scales WHERE year = ? AND scale_type = 'ahorro'",
        [year]
    )

    ahorro_inserted = 0
    # Estatal ahorro
    for tramo_num, base_hasta, cuota_integra, resto_base, tipo in AHORRO_ESTATAL_2024:
        await db.execute(
            "INSERT INTO irpf_scales (id, jurisdiction, year, scale_type, tramo_num, "
            "base_hasta, cuota_integra, resto_base, tipo_aplicable) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [str(uuid.uuid4()), "Estatal", year, "ahorro", tramo_num,
             base_hasta, cuota_integra, resto_base, tipo]
        )
        ahorro_inserted += 1

    # Autonómico ahorro (escala complementaria estándar para CCAAs régimen común)
    ccaa_regimen_comun = [
        "Andalucía", "Aragón", "Asturias", "Baleares", "Canarias",
        "Cantabria", "Castilla y León", "Castilla-La Mancha",
        "Cataluña", "Extremadura", "Galicia", "La Rioja",
        "Comunidad de Madrid", "Murcia", "Comunitat Valenciana",
    ]
    for ccaa in ccaa_regimen_comun:
        for tramo_num, base_hasta, cuota_integra, resto_base, tipo in AHORRO_AUTONOMICO_2024:
            await db.execute(
                "INSERT INTO irpf_scales (id, jurisdiction, year, scale_type, tramo_num, "
                "base_hasta, cuota_integra, resto_base, tipo_aplicable) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [str(uuid.uuid4()), ccaa, year, "ahorro", tramo_num,
                 base_hasta, cuota_integra, resto_base, tipo]
            )
            ahorro_inserted += 1

    print(f"  ✓ {ahorro_inserted} filas tarifa ahorro (estatal + {len(ccaa_regimen_comun)} CCAAs)")

    # --- Verification ---
    print(f"\n{'='*60}")
    print("🔍 Verificación:")
    result = await db.execute(
        "SELECT category, COUNT(*) as cnt FROM tax_parameters WHERE year = ? GROUP BY category",
        [year]
    )
    for row in result.rows:
        print(f"  tax_parameters/{row['category']}: {row['cnt']} registros")

    result = await db.execute(
        "SELECT scale_type, COUNT(*) as cnt FROM irpf_scales WHERE year = ? GROUP BY scale_type",
        [year]
    )
    for row in result.rows:
        print(f"  irpf_scales/{row['scale_type']}: {row['cnt']} registros")

    print(f"\n✅ Total tax_parameters insertados: {inserted}")
    print(f"✅ Total ahorro scales insertadas: {ahorro_inserted}")

    # Test query
    print("\n🧪 Test: MPYF contribuyente Estatal...")
    result = await db.execute(
        "SELECT value FROM tax_parameters WHERE category='mpyf' AND param_key='contribuyente' AND year=? AND jurisdiction='Estatal'",
        [year]
    )
    if result.rows:
        print(f"  ✓ contribuyente = {result.rows[0]['value']}€")

    print("\n🧪 Test: MPYF contribuyente Comunitat Valenciana...")
    result = await db.execute(
        "SELECT value FROM tax_parameters WHERE category='mpyf' AND param_key='contribuyente' AND year=? AND jurisdiction='Comunitat Valenciana'",
        [year]
    )
    if result.rows:
        print(f"  ✓ contribuyente = {result.rows[0]['value']}€ (override autonómico)")

    print("\n🧪 Test: Tarifa ahorro estatal tramo 1...")
    result = await db.execute(
        "SELECT tipo_aplicable FROM irpf_scales WHERE jurisdiction='Estatal' AND year=? AND scale_type='ahorro' AND tramo_num=1",
        [year]
    )
    if result.rows:
        print(f"  ✓ tipo_aplicable = {result.rows[0]['tipo_aplicable']}%")

    await db.disconnect()
    print(f"\n{'='*60}")
    print("✅ Population complete!")


if __name__ == "__main__":
    asyncio.run(populate())
