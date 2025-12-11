"""
Database migration: Add payslips table.

Run with:
    python scripts/add_payslips_table.py
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


async def add_payslips_table():
    print("📝 Añadiendo tabla payslips...")
    
    db = TursoClient()
    await db.connect()
    
    try:
        # Create table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS payslips (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                filename TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                upload_date TEXT DEFAULT (datetime('now')),
                
                -- Datos extraídos del PDF
                period_month INTEGER,
                period_year INTEGER,
                company_name TEXT,
                company_cif TEXT,
                employee_name TEXT,
                employee_nif TEXT,
                employee_ss TEXT,
                
                -- Cantidades económicas
                gross_salary REAL,
                net_salary REAL,
                base_salary REAL,
                irpf_withholding REAL,
                irpf_percentage REAL,
                ss_contribution REAL,
                unemployment_contribution REAL,
                extra_payments REAL,
                overtime_pay REAL,
                
                -- Metadata
                extraction_status TEXT CHECK(extraction_status IN ('pending', 'processing', 'completed', 'failed')) DEFAULT 'pending',
                extracted_data TEXT,  -- JSON con todos los datos extraídos
                analysis_summary TEXT,
                error_message TEXT,
                
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        
        print("✅ Tabla creada")
        
        # Create indexes
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payslips_user 
            ON payslips(user_id, created_at DESC)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payslips_period 
            ON payslips(period_year, period_month)
        """)
        
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_payslips_status 
            ON payslips(extraction_status)
        """)
        
        print("✅ Índices creados")
        print("\n✅ Migración completada!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise
    
    finally:
        await db.disconnect()


if __name__ == "__main__":
    asyncio.run(add_payslips_table())
