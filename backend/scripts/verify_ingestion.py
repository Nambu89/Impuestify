"""
Comprehensive verification of PDF ingestion coverage.

Checks:
1. Total page coverage per document (target: >95%)
2. Specific critical sections (e.g., Chapter 15 IRPF tables)
3. Table extraction validation
4. FTS5 index completeness
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


async def verify_ingestion():
    print("=" * 70)
    print("PDF INGESTION VERIFICATION REPORT")
    print("=" * 70)
    print()
    
    turso_url = os.environ.get("TURSO_DATABASE_URL")
    turso_token = os.environ.get("TURSO_AUTH_TOKEN")
    
    db = TursoClient(turso_url, turso_token)
    await db.connect()
    
    # 1. Overall Statistics
    print("📊 OVERALL STATISTICS")
    print("-" * 70)
    
    stats_sql = """
    SELECT 
        COUNT(DISTINCT d.id) as total_docs,
        SUM(d.total_pages) as total_pages,
        COUNT(c.id) as total_chunks,
        COUNT(DISTINCT c.page_number) as unique_pages_with_chunks
    FROM documents d
    LEFT JOIN document_chunks c ON c.document_id = d.id
    """
    
    stats = await db.execute(stats_sql)
    s = stats.rows[0]
    
    print(f"  Documents: {s['total_docs']}")
    print(f"  Total Pages (expected): {s['total_pages']}")
    print(f"  Unique Pages with Chunks: {s['unique_pages_with_chunks']}")
    print(f"  Total Chunks: {s['total_chunks']}")
    print(f"  Average Chunks per Page: {s['total_chunks'] / max(s['unique_pages_with_chunks'], 1):.1f}")
    print()
    
    # 2. Per-Document Coverage
    print("📄 PER-DOCUMENT COVERAGE")
    print("-" * 70)
    
    coverage_sql = """
    SELECT 
        d.filename,
        d.total_pages,
        COUNT(DISTINCT c.page_number) as indexed_pages,
        COUNT(c.id) as chunk_count,
        ROUND(COUNT(DISTINCT c.page_number) * 100.0 / NULLIF(d.total_pages, 0), 1) as coverage_pct
    FROM documents d
    LEFT JOIN document_chunks c ON c.document_id = d.id
    GROUP BY d.id, d.filename, d.total_pages
    ORDER BY coverage_pct ASC, d.filename
    """
    
    coverage = await db.execute(coverage_sql)
    
    issues = []
    perfect = []
    
    for row in coverage.rows:
        coverage_pct = row['coverage_pct'] or 0
        status = "✅" if coverage_pct >= 95 else "⚠️" if coverage_pct >= 80 else "❌"
        
        print(f"  {status} {row['filename'][:50]:<50} {row['indexed_pages']:>4}/{row['total_pages']:<4} ({coverage_pct:>5.1f}%) - {row['chunk_count']} chunks")
        
        if coverage_pct < 95:
            issues.append(row['filename'])
        elif coverage_pct >= 99:
            perfect.append(row['filename'])
    
    print()
    print(f"  Summary: {len(perfect)} perfect, {len(issues)} issues")
    print()
    
    # 3. Critical Section Validation (Chapter 15 IRPF)
    print("🔍 CRITICAL SECTION: Capítulo 15 - Cálculo del impuesto")
    print("-" * 70)
    
    chapter15_sql = """
    SELECT 
        c.page_number,
        c.content,
        LENGTH(c.content) as char_count
    FROM document_chunks c
    JOIN documents d ON d.id = c.document_id
    WHERE d.filename LIKE '%Renta_2024._Parte_1%'
    AND c.page_number BETWEEN 1230 AND 1240
    ORDER BY c.page_number, c.chunk_index
    """
    
    chapter15 = await db.execute(chapter15_sql)
    
    if chapter15.rows:
        print(f"  ✅ Found {len(chapter15.rows)} chunks in pages 1230-1240")
        
        # Check for specific content (IRPF scale table)
        has_scale = False
        for row in chapter15.rows:
            if "escala general" in row['content'].lower() and "12.450" in row['content']:
                has_scale = True
                print(f"  ✅ IRPF scale table found on page {row['page_number']}")
                print(f"     Preview: {row['content'][:150].replace(chr(10), ' ')}...")
                break
        
        if not has_scale:
            print("  ⚠️  IRPF scale table NOT detected (may need manual verification)")
    else:
        print("  ❌ NO chunks found in pages 1230-1240!")
        print("     This is a CRITICAL issue - Chapter 15 not indexed")
    
    print()
    
    # 4. Table Detection
    print("📊 TABLE DETECTION")
    print("-" * 70)
    
    table_sql = """
    SELECT 
        d.filename,
        COUNT(CASE WHEN c.content LIKE '%|%' THEN 1 END) as chunks_with_tables
    FROM documents d
    LEFT JOIN document_chunks c ON c.document_id = d.id
    GROUP BY d.filename
    HAVING chunks_with_tables > 0
    ORDER BY chunks_with_tables DESC
    LIMIT 10
    """
    
    tables = await db.execute(table_sql)
    
    print("  Top documents with tables (Markdown format '|'):")
    for row in tables.rows:
        print(f"    {row['filename'][:55]:<55} {row['chunks_with_tables']:>4} chunks")
    
    print()
    
    # 5. FTS5 Index Status
    print("🔎 FTS5 SEARCH INDEX")
    print("-" * 70)
    
    fts_sql = "SELECT COUNT(*) as fts_count FROM document_chunks_fts"
    fts_result = await db.execute(fts_sql)
    fts_count = fts_result.rows[0]['fts_count']
    
    if fts_count == s['total_chunks']:
        print(f"  ✅ FTS5 index complete: {fts_count} entries")
    elif fts_count == 0:
        print(f"  ❌ FTS5 index EMPTY - Run rebuild_fts5.py")
    else:
        print(f"  ⚠️  FTS5 index incomplete: {fts_count}/{s['total_chunks']}")
    
    print()
    
    # 6. Final Verdict
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    
    if len(issues) == 0 and fts_count == s['total_chunks'] and chapter15.rows:
        print("✅ ALL CHECKS PASSED")
        print("   - All documents have >95% coverage")
        print("   - Critical sections indexed")
        print("   - FTS5 index complete")
        print()
        print("🎉 System ready for production!")
    else:
        print("⚠️  ISSUES DETECTED:")
        if issues:
            print(f"   - {len(issues)} documents with <95% coverage")
        if not chapter15.rows:
            print("   - Chapter 15 NOT indexed")
        if fts_count != s['total_chunks']:
            print("   - FTS5 index incomplete")
        print()
        print("Action required: Review issues above")
    
    print("=" * 70)
    
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(verify_ingestion())
