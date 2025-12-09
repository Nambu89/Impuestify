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

async def analyze_coverage():
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    
    # Get page coverage for Manual Renta Parte 1
    sql = """
    SELECT 
        MIN(c.page_number) as min_page,
        MAX(c.page_number) as max_page,
        COUNT(DISTINCT c.page_number) as unique_pages,
        COUNT(c.id) as total_chunks,
        d.total_pages
    FROM document_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE d.filename = 'Manual_práctico_de_Renta_2024._Parte_1.pdf'
    GROUP BY d.total_pages
    """
    
    result = await db.execute(sql)
    
    if result.rows:
        row = result.rows[0]
        print("📊 Manual_práctico_de_Renta_2024._Parte_1.pdf Coverage:")
        print(f"   Total pages in document: {row['total_pages']}")
        print(f"   Pages with chunks: {row['unique_pages']}")
        print(f"   Page range: {row['min_page']} - {row['max_page']}")
        print(f"   Total chunks: {row['total_chunks']}")
        print(f"   Coverage: {(row['unique_pages'] / row['total_pages'] * 100):.1f}%")
        
        # Check specific problematic range
        print("\n🔍 Checking pages 1200-1300 specifically...")
        sql2 = """
        SELECT DISTINCT c.page_number
        FROM document_chunks c
        JOIN documents d ON d.id = c.document_id
        WHERE d.filename = 'Manual_práctico_de_Renta_2024._Parte_1.pdf'
        AND c.page_number BETWEEN 1200 AND 1300
        ORDER BY c.page_number
        """
        
        result2 = await db.execute(sql2)
        pages = [row['page_number'] for row in result2.rows]
        
        if pages:
            print(f"   Found {len(pages)} pages in range 1200-1300")
            print(f"   Pages: {pages[:20]}..." if len(pages) > 20 else f"   Pages: {pages}")
            
            # Check for gaps
            missing = []
            for p in range(1200, 1300):
                if p not in pages:
                    missing.append(p)
            
            if missing:
                print(f"\n   ⚠️ Missing {len(missing)} pages in 1200-1300 range")
                print(f"   Missing pages sample: {missing[:20]}")
        else:
            print("   ❌ NO pages found in 1200-1300 range!")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(analyze_coverage())
