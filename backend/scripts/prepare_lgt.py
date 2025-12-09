"""
Simple script to run extract_pdfs_v2.py on data/lgt/ folder specifically.
"""
import subprocess
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent
project_root = backend_dir.parent

lgt_dir = project_root / "data" / "lgt"

if not lgt_dir.exists():
    print(f"❌ Directory not found: {lgt_dir}")
    print("   Please create data/lgt/ and add LGT PDFs there")
    sys.exit(1)

pdf_files = list(lgt_dir.glob("*.pdf"))

if not pdf_files:
    print(f"⚠️  No PDF files found in {lgt_dir}")
    sys.exit(0)

print("=" * 70)
print("INGESTING LGT DOCUMENTS")
print("=" * 70)
print(f"\n📚 Found {len(pdf_files)} PDF file(s) in data/lgt/\n")

# Move PDFs temporarily to main data/ folder for processing
import shutil

temp_moved = []
for pdf in pdf_files:
    dest = project_root / "data" / pdf.name
    if not dest.exists():
        shutil.copy(pdf, dest)
        temp_moved.append(dest)
        print(f"   Copied: {pdf.name}")

print(f"\n✅ Ready to ingest {len(temp_moved)} new LGT documents\n")
print("Run: python scripts/extract_pdfs_v2.py")
print("\n" + "=" * 70)
