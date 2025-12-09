"""
Extract Estatal (state) IRPF scale from page 1235.
Quick targeted extraction to complete the scales.
"""
import asyncio
import os
import sys
import uuid
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

project_root = backend_dir.parent
load_dotenv(project_root / ".env")

from app.database.turso_client import TursoClient
from scripts.extract_structured_tables import TableExtractor, IRPFScaleParser


async def extract_estatal_scale():
    """Extract only the Estatal scale from page 1235."""
    print("=" * 70)
    print("EXTRACCIÓN ESCALA ESTATAL")
    print("=" * 70)
    print()
    
    data_dir = project_root / "data"
    manual_renta = data_dir / "Manual_práctico_de_Renta_2024._Parte_1.pdf"
    
    if not manual_renta.exists():
        print(f"❌ File not found: {manual_renta}")
        return
    
    # Extract tables
    extractor = TableExtractor()
    parser = IRPFScaleParser()
    
    print("📄 Extracting tables from Manual Renta...")
    tables = extractor.extract_tables_from_pdf(str(manual_renta))
    
    # Filter for page 1235 only
    page_1235_tables = [t for t in tables if t['page_number'] == 1235]
    
    print(f"📍 Found {len(page_1235_tables)} table(s) on page 1235\n")
    
    # Connect to DB
    db = TursoClient()
    await db.connect()
    
    # Process tables
    for i, table in enumerate(page_1235_tables, 1):
        print(f"📊 Table {i}: {table['row_count']}x{table['column_count']}")
        
        # Check headers
        first_row = [c for c in table['cells'] if c['row'] == 0]
        headers = ' '.join([c['content'].lower() for c in sorted(first_row, key=lambda x: x['col'])])
        print(f"   Headers: {headers[:100]}...")
        
        # Must have IRPF scale keywords
        if not ('base' in headers and 'liquidable' in headers and 'cuota' in headers):
            print(f"   ⏭️  Skipping (not IRPF scale)\n")
            continue
        
        # Parse table
        try:
            parsed_rows = parser.parse_scale_table(table)
            
            if not parsed_rows:
                print(f"   ⚠️  No valid rows parsed\n")
                continue
            
            print(f"   ✅ Parsed {len(parsed_rows)} tramos")
            
            # Insert as Estatal
            for tramo_num, row in enumerate(parsed_rows, 1):
                scale_id = str(uuid.uuid4())
                
                await db.execute("""
                    INSERT INTO irpf_scales 
                    (id, jurisdiction, year, scale_type, tramo_num,
                     base_hasta, cuota_integra, resto_base, tipo_aplicable)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    scale_id,
                    'Estatal',
                    2024,
                    'general',
                    tramo_num,
                    row['base_hasta'],
                    row['cuota_integra'],
                    row['resto_base'],
                    row['tipo_aplicable']
                ])
            
            print(f"   ✅ Inserted {len(parsed_rows)} tramos as 'Estatal'\n")
            
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            import traceback
            traceback.print_exc()
    
    await db.disconnect()
    
    print("=" * 70)
    print("✅ EXTRACTION COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(extract_estatal_scale())
