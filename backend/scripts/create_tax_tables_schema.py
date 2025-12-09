"""
Create SQL schema for structured tax tables.
"""
import asyncio
import os
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient


async def create_tax_tables_schema():
    print("📝 Creating tax tables schema...\n")
    
    db = TursoClient()
    await db.connect()
    
    try:
        # 1. IRPF Scales table
        print("Creating irpf_scales table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS irpf_scales (
                id TEXT PRIMARY KEY,
                jurisdiction TEXT NOT NULL,
                year INTEGER NOT NULL,
                scale_type TEXT NOT NULL,
                tramo_num INTEGER NOT NULL,
                base_hasta REAL NOT NULL,
                cuota_integra REAL NOT NULL,
                resto_base REAL NOT NULL,
                tipo_aplicable REAL NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ irpf_scales created\n")
        
        # Create indexes
        print("Creating indexes...")
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_irpf_jurisdiction_year 
            ON irpf_scales(jurisdiction, year, scale_type)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_irpf_year 
            ON irpf_scales(year)
        """)
        print("✅ Indexes created\n")
        
        # 2. IVA Rates table (for future)
        print("Creating iva_rates table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS iva_rates (
                id TEXT PRIMARY KEY,
                year INTEGER NOT NULL,
                tipo TEXT NOT NULL,
                porcentaje REAL NOT NULL,
                descripcion TEXT,
                ejemplos TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ iva_rates created\n")
        
        # 3. Retentions table (for future)
        print("Creating irpf_retentions table...")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS irpf_retentions (
                id TEXT PRIMARY KEY,
                year INTEGER NOT NULL,
                tipo_renta TEXT NOT NULL,
                condicion TEXT,
                tipo_retencion REAL NOT NULL,
                observaciones TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ irpf_retentions created\n")
        
        print("=" * 60)
        print("✅ ALL TABLES CREATED SUCCESSFULLY")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(create_tax_tables_schema())
