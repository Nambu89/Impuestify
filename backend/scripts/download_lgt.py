"""
Download Ley General Tributaria from AEAT.

URL: https://sede.agenciatributaria.gob.es/Sede/normativa-criterios-interpretativos/ley-general-tributaria-normas-desarrollo/ley-general-tributaria.html

This is the tax legal framework needed for complex scenarios like:
- Multiple payers
- Special deductions  
- Tax procedures
"""
import asyncio
import requests
import os
from pathlib import Path
from dotenv import load_dotenv

# Load env
project_root = Path(__file__).parent.parent.parent
load_dotenv(project_root / ".env")

def download_lgt():
    """Download LGT PDF from BOE."""
    print("=" * 70)
    print("DESCARGA LEY GENERAL TRIBUTARIA")
    print("=" * 70)
    print()
    
    # BOE consolidated text URL
    url = "https://www.boe.es/buscar/pdf/2003/BOE-A-2003-23186-consolidado.pdf"
    
    data_dir = project_root / "data"
    data_dir.mkdir(exist_ok=True)
    
    output_path = data_dir / "Ley_General_Tributaria_2003_consolidado.pdf"
    
    if output_path.exists():
        print(f"✅ LGT already downloaded: {output_path}")
        print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB\n")
        return str(output_path)
    
    print(f"📥 Downloading from: {url}")
    print()
    
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        
        with open(output_path, 'wb') as f:
            downloaded = 0
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size:
                        percent = (downloaded / total_size) * 100
                        print(f"\rProgress: {percent:.1f}% ({downloaded / 1024:.1f} KB)", end='')
        
        print(f"\n\n✅ Downloaded successfully: {output_path}")
        print(f"   Size: {output_path.stat().st_size / 1024:.1f} KB")
        print()
        
        return str(output_path)
        
    except Exception as e:
        print(f"❌ Error downloading LGT: {e}")
        return None


if __name__ == "__main__":
    pdf_path = download_lgt()
    
    if pdf_path:
        print("=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print(f"1. Run: python scripts/extract_pdfs_v2.py")
        print(f"2. LGT will be ingested with other PDFs")
        print(f"3. Rebuild FTS5: python scripts/rebuild_fts5.py")
        print("=" * 70)
