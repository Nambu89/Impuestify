"""Audit Turso DB documents and identify gaps"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

async def audit_docs():
    from app.database.turso_client import TursoClient
    db = TursoClient()
    await db.connect()
    
    print("=" * 70)
    print("AUDITORIA DE DOCUMENTOS EN TURSO DB")
    print("=" * 70)
    
    # Get all documents with chunk counts
    result = await db.execute("""
        SELECT 
            d.id,
            d.filename,
            d.title,
            COUNT(c.id) as chunk_count
        FROM documents d
        LEFT JOIN document_chunks c ON c.document_id = d.id
        GROUP BY d.id
        ORDER BY d.filename
    """)
    
    print("\n=== DOCUMENTOS ACTUALES ===\n")
    
    # Categorize documents
    categories = {
        'irpf': [],
        'iva': [],
        'sociedades': [],
        'patrimonio': [],
        'iae': [],
        'forales_bizkaia': [],
        'forales_gipuzkoa': [],
        'forales_araba': [],
        'forales_navarra': [],
        'ceuta_melilla': [],
        'verifactu_ticketbai': [],
        'general': [],
        'otros': []
    }
    
    for row in result.rows:
        fname = row['filename'].lower()
        chunks = row['chunk_count']
        doc = f"{row['filename']} ({chunks} chunks)"
        
        if 'bizkaia' in fname:
            categories['forales_bizkaia'].append(doc)
        elif 'guipuzkoa' in fname or 'gipuzkoa' in fname:
            categories['forales_gipuzkoa'].append(doc)
        elif 'araba' in fname or 'alaba' in fname or 'alava' in fname:
            categories['forales_araba'].append(doc)
        elif 'navarra' in fname:
            categories['forales_navarra'].append(doc)
        elif 'ceuta' in fname or 'melilla' in fname:
            categories['ceuta_melilla'].append(doc)
        elif 'renta' in fname or 'irpf' in fname:
            categories['irpf'].append(doc)
        elif 'iva' in fname:
            categories['iva'].append(doc)
        elif 'sociedad' in fname:
            categories['sociedades'].append(doc)
        elif 'patrimonio' in fname:
            categories['patrimonio'].append(doc)
        elif 'iae' in fname or 'actividades' in fname:
            categories['iae'].append(doc)
        elif 'verifactu' in fname or 'ticketbai' in fname or 'batuz' in fname:
            categories['verifactu_ticketbai'].append(doc)
        elif 'boe' in fname or 'ley' in fname or 'tributaria' in fname:
            categories['general'].append(doc)
        else:
            categories['otros'].append(doc)
    
    for cat, docs in categories.items():
        if docs:
            print(f"\n--- {cat.upper().replace('_', ' ')} ({len(docs)} docs) ---")
            for d in docs:
                print(f"  - {d}")
    
    print("\n" + "=" * 70)
    print("RESUMEN")
    print("=" * 70)
    print(f"Total documentos: {len(result.rows)}")
    
    # Count by category
    for cat, docs in categories.items():
        if docs:
            print(f"  {cat}: {len(docs)}")
    
    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(audit_docs())
