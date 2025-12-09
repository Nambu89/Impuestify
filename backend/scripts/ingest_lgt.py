"""
Ingest PDFs from data/lgt/ subfolder (Ley General Tributaria).

This processes LGT documents separately to tag them properly.
"""
import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

project_root = backend_dir.parent
load_dotenv(project_root / ".env")

# Import the extraction logic
from scripts.extract_pdfs_v2 import process_pdf


async def ingest_lgt():
    """Ingest LGT documents from data/lgt/"""
    print("=" * 70)
    print("INGESTION: LEY GENERAL TRIBUTARIA")
    print("=" * 70)
    print()
    
    lgt_dir = project_root / "data" / "lgt"
    
    if not lgt_dir.exists():
        print(f"❌ Directory not found: {lgt_dir}")
        print(f"   Please create it and add LGT PDFs there")
        return
    
    # Find all PDFs
    pdf_files = list(lgt_dir.glob("*.pdf"))
    
    if not pdf_files:
        print(f"⚠️  No PDF files found in {lgt_dir}")
        return
    
    print(f"📚 Found {len(pdf_files)} PDF file(s):\n")
    for pdf in pdf_files:
        print(f"   - {pdf.name}")
    print()
    
    # Process each PDF
    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] Processing {pdf_path.name}...")
        
        try:
            await process_pdf(
                pdf_path=str(pdf_path),
                category="normativa",  # Tag as legal framework
                source="BOE - Ley General Tributaria"
            )
            print(f"   ✅ Completed\n")
        except Exception as e:
            print(f"   ❌ Error: {e}\n")
            continue
    
    print("=" * 70)
    print("✅ LGT INGESTION COMPLETED")
    print("=" * 70)
    print("\n🔄 Next: Rebuild FTS5 index")
    print("   python scripts/rebuild_fts5.py\n")


if __name__ == "__main__":
    asyncio.run(ingest_lgt())
