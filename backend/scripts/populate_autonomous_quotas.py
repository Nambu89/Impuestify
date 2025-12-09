"""
Populate autonomous_quotas table with 2025 data.

This script inserts the 15 income brackets for autonomous workers
in Spain for 2025, including special bonuses for Ceuta and Melilla.

Data source: Infoautónomos and official Seguridad Social tables.
"""
import asyncio
import os
import sys
from pathlib import Path

# Setup path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient

# 2025 Autonomous Quotas Data (15 tramos)
# Source: https://www.infoautonomos.com/seguridad-social/cuota-de-autonomos-cuanto-se-paga/
TRAMOS_2025 = [
    # Tramo, Rendimientos Min, Rendimientos Max, Base Min, Base Max, Cuota Min, Cuota Max
    (1, 0, 670, 653.59, 718.94, 200.00, 226.00),
    (2, 670, 900, 700.00, 1000.00, 220.00, 314.00),
    (3, 900, 1166.70, 826.67, 1000.00, 260.00, 314.00),
    (4, 1166.70, 1300, 926.67, 1000.00, 291.00, 314.00),
    (5, 1300, 1500, 935.00, 1000.00, 294.00, 314.00),
    (6, 1500, 1700, 960.78, 1000.00, 302.00, 314.00),
    (7, 1700, 1850, 1013.07, 1045.75, 318.00, 329.00),
    (8, 1850, 2030, 1029.41, 1078.43, 323.00, 339.00),
    (9, 2030, 2330, 1045.75, 1143.79, 329.00, 359.00),
    (10, 2330, 2760, 1111.11, 1307.19, 349.00, 411.00),
    (11, 2760, 3190, 1176.47, 1405.88, 370.00, 442.00),
    (12, 3190, 3620, 1241.83, 1504.58, 390.00, 473.00),
    (13, 3620, 4050, 1307.19, 1635.29, 411.00, 514.00),
    (14, 4050, 6000, 1372.55, 1928.10, 431.00, 606.00),
    (15, 6000, None, 1633.99, 4909.50, 513.00, 1542.00),  # Last tramo has no max
]


async def populate_quotas():
    """Populate the autonomous_quotas table with 2025 data."""
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    if not turso_url or not turso_token:
        print("❌ Missing TURSO_DATABASE_URL or TURSO_AUTH_TOKEN")
        return
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    print("✅ Connected to Turso")
    
    # Clear existing 2025 data
    print("🧹 Clearing existing 2025 data...")
    await db.execute("DELETE FROM autonomous_quotas WHERE year = 2025")
    
    # Insert general (España común) tramos
    print("\n📊 Inserting 15 tramos for general Spain...")
    for tramo_data in TRAMOS_2025:
        tramo_num, rend_min, rend_max, base_min, base_max, cuota_min, cuota_max = tramo_data
        
        sql = """
        INSERT INTO autonomous_quotas (
            year, tramo_number, 
            rendimientos_netos_min, rendimientos_netos_max,
            base_cotizacion_min, base_cotizacion_max,
            cuota_min, cuota_max,
            region, bonificacion_percent,
            cuota_min_bonificada, cuota_max_bonificada
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await db.execute(sql, [
            2025, tramo_num,
            rend_min, rend_max,
            base_min, base_max,
            cuota_min, cuota_max,
            'general', 0,  # No bonificación
            None, None  # No cuota bonificada
        ])
        
        print(f"  ✓ Tramo {tramo_num}: {rend_min}€ - {rend_max or '∞'}€ → Cuota: {cuota_min}€ - {cuota_max}€")
    
    # Insert Ceuta tramos (50% bonificación en contingencias comunes)
    print("\n🎁 Inserting 15 tramos for Ceuta (50% bonus)...")
    for tramo_data in TRAMOS_2025:
        tramo_num, rend_min, rend_max, base_min, base_max, cuota_min, cuota_max = tramo_data
        
        # Calculate bonified quotas (50% discount on contingencias comunes)
        # Contingencias comunes = 28.30% of base
        # Other contributions = 3.10% of base (not bonified)
        # Total normal = 31.40%
        # Bonified = (28.30% * 0.5) + 3.10% = 17.25%
        
        cuota_min_bonificada = round(base_min * 0.1725, 2)
        cuota_max_bonificada = round(base_max * 0.1725, 2)
        
        sql = """
        INSERT INTO autonomous_quotas (
            year, tramo_number, 
            rendimientos_netos_min, rendimientos_netos_max,
            base_cotizacion_min, base_cotizacion_max,
            cuota_min, cuota_max,
            region, bonificacion_percent,
            cuota_min_bonificada, cuota_max_bonificada
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await db.execute(sql, [
            2025, tramo_num,
            rend_min, rend_max,
            base_min, base_max,
            cuota_min, cuota_max,
            'ceuta', 50,
            cuota_min_bonificada, cuota_max_bonificada
        ])
        
        print(f"  ✓ Tramo {tramo_num}: {rend_min}€ - {rend_max or '∞'}€ → Cuota bonificada: {cuota_min_bonificada}€ - {cuota_max_bonificada}€")
    
    # Insert Melilla tramos (50% bonificación)
    print("\n🎁 Inserting 15 tramos for Melilla (50% bonus)...")
    for tramo_data in TRAMOS_2025:
        tramo_num, rend_min, rend_max, base_min, base_max, cuota_min, cuota_max = tramo_data
        
        cuota_min_bonificada = round(base_min * 0.1725, 2)
        cuota_max_bonificada = round(base_max * 0.1725, 2)
        
        sql = """
        INSERT INTO autonomous_quotas (
            year, tramo_number, 
            rendimientos_netos_min, rendimientos_netos_max,
            base_cotizacion_min, base_cotizacion_max,
            cuota_min, cuota_max,
            region, bonificacion_percent,
            cuota_min_bonificada, cuota_max_bonificada
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        await db.execute(sql, [
            2025, tramo_num,
            rend_min, rend_max,
            base_min, base_max,
            cuota_min, cuota_max,
            'melilla', 50,
            cuota_min_bonificada, cuota_max_bonificada
        ])
        
        print(f"  ✓ Tramo {tramo_num}: {rend_min}€ - {rend_max or '∞'}€ → Cuota bonificada: {cuota_min_bonificada}€ - {cuota_max_bonificada}€")
    
    # Verify
    print("\n🔍 Verifying data...")
    result = await db.execute("SELECT COUNT(*) as count FROM autonomous_quotas WHERE year = 2025")
    count = result.rows[0]['count']
    print(f"✅ Total records inserted: {count} (expected: 45 = 15 tramos × 3 regions)")
    
    # Test query
    print("\n🧪 Testing query for 1500€ income in general region...")
    test_sql = """
    SELECT tramo_number, cuota_min, cuota_max
    FROM autonomous_quotas
    WHERE year = 2025 AND region = 'general'
    AND rendimientos_netos_min <= 1500
    AND (rendimientos_netos_max >= 1500 OR rendimientos_netos_max IS NULL)
    """
    result = await db.execute(test_sql)
    if result.rows:
        row = result.rows[0]
        print(f"  ✓ Tramo {row['tramo_number']}: Cuota {row['cuota_min']}€ - {row['cuota_max']}€")
    
    await db.disconnect()
    print("\n✅ Population complete!")


if __name__ == "__main__":
    asyncio.run(populate_quotas())
