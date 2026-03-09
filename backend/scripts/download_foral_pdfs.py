"""
DEPRECATED — Use doc_crawler instead:
    python -m backend.scripts.doc_crawler [options]

This script has hardcoded paths and limited URL coverage.
See backend/scripts/doc_crawler/ for the automated replacement.

---
Original: Script para descargar PDFs de las Haciendas Forales.
"""
import os
import sys
import requests
from pathlib import Path
from typing import List, Tuple

# Directorio de destino
DATA_DIR = Path(r"C:\Users\fprada\OneDrive - Devoteam Group\Documents\Proyectos\TaxIA\data")


# URLs de PDFs conocidas (las que tienen enlace directo)
PDFS_TO_DOWNLOAD: List[Tuple[str, str, str]] = [
    # (url, nombre_archivo, subcarpeta)
    
    # === NAVARRA ===
    # Manual teórico Renta 2024
    (
        "https://www.navarra.es/documents/48192/17863227/Manual+te%C3%B3rico+de+la+campa%C3%B1a+de+2024.pdf",
        "Navarra_Manual_teorico_Renta_2024.pdf",
        "Navarra"
    ),
    
    # === AEAT - Adicionales ===
    # Manual No Residentes (que faltaba)
    (
        "https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/Manual/Practicos/No_Residentes/Manual_No_Residentes.pdf",
        "Manual_No_Residentes_2024.pdf",
        ""
    ),
    
    # Manual Patrimonio 2024 (versión PDF directa)
    (
        "https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/Manual/Practicos/Patrimonio/Patrimonio-2024/ManualPatrimonio2024_es_es.pdf",
        "Manual_Patrimonio_2024_AEAT.pdf",
        ""
    ),
    
    # Manual Sociedades 2024 (PDF directo)
    (
        "https://sede.agenciatributaria.gob.es/static_files/Sede/Biblioteca/Manual/Practicos/Sociedades/Manual_Sociedades_2024.pdf",
        "Manual_Sociedades_2024_AEAT.pdf",
        ""
    ),
]

# URLs que requieren navegación manual (no tienen PDF directo)
MANUAL_DOWNLOAD_URLS = {
    "Bizkaia": [
        {
            "descripcion": "Instrucciones DG Hacienda",
            "url": "https://www.bizkaia.eus/es/web/hacienda-y-finanzas/instrucciones-direccion-general-hacienda",
            "nota": "Buscar 'Instrucción 1/2025' o 'Instrucción 1/2024'"
        },
        {
            "descripcion": "Normativa IRPF",
            "url": "https://www.bizkaia.eus/es/web/hacienda-y-finanzas/irpf/normativa",
            "nota": "Descargar Norma Foral 13/2013 actualizada"
        }
    ],
    "Gipuzkoa": [
        {
            "descripcion": "Normativa tributaria",
            "url": "https://www.gipuzkoa.eus/es/web/ogasuna/-/araudia-2",
            "nota": "Buscar Norma Foral 1/2025 y descargar PDF"
        },
        {
            "descripcion": "Manual IRPF",
            "url": "https://www.gipuzkoa.eus/es/web/ogasuna/irpf/manuales",
            "nota": "Descargar Manual de divulgación 2024"
        }
    ],
    "Araba": [
        {
            "descripcion": "Renta 2024 - Manual y normativa",
            "url": "https://web.araba.eus/es/hacienda/renta-patrimonio-2024",
            "nota": "Descargar Manual y Normativa"
        },
        {
            "descripcion": "Normativa general",
            "url": "https://web.araba.eus/es/hacienda/normativa",
            "nota": "Buscar Norma Foral 19/2024"
        }
    ],
    "Navarra": [
        {
            "descripcion": "Manuales adicionales",
            "url": "https://www.navarra.es/es/tramites/on/-/stamp/IdiomaRecurso/es_ES/IdiomaNavegacion/es/Tema/27/Procedimiento/496",
            "nota": "Si hay más manuales disponibles"
        }
    ]
}


def create_directories():
    """Crea las carpetas necesarias."""
    subdirs = ["Navarra", "Bizkaia", "Gipuzkoa", "Araba"]
    
    for subdir in subdirs:
        dir_path = DATA_DIR / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Carpeta creada/verificada: {dir_path}")


def download_pdf(url: str, filename: str, subfolder: str = "") -> bool:
    """
    Descarga un PDF desde una URL.
    
    Returns:
        True si descarga exitosa, False si error
    """
    try:
        # Determinar ruta de destino
        if subfolder:
            dest_path = DATA_DIR / subfolder / filename
        else:
            dest_path = DATA_DIR / filename
        
        # Verificar si ya existe
        if dest_path.exists():
            print(f"   ⏭️  Ya existe: {filename}")
            return True
        
        print(f"   📥 Descargando: {filename}...")
        
        # Headers para simular navegador
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/pdf,*/*",
        }
        
        # Descargar
        response = requests.get(url, headers=headers, timeout=60, allow_redirects=True)
        response.raise_for_status()
        
        # Verificar que es un PDF
        content_type = response.headers.get("Content-Type", "")
        if "pdf" not in content_type.lower() and not response.content[:4] == b"%PDF":
            print(f"   ⚠️  No es un PDF válido: {url}")
            return False
        
        # Guardar
        with open(dest_path, "wb") as f:
            f.write(response.content)
        
        size_mb = len(response.content) / (1024 * 1024)
        print(f"   ✅ Descargado: {filename} ({size_mb:.1f} MB)")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Error descargando {filename}: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error inesperado: {e}")
        return False


def main():
    print("=" * 60)
    print("TaxIA - Descarga de PDFs Haciendas Forales")
    print("=" * 60)
    print(f"\nDestino: {DATA_DIR}\n")
    
    # Crear carpetas
    print("📁 Creando estructura de carpetas...")
    create_directories()
    print()
    
    # Descargar PDFs con URL directa
    print("📥 Descargando PDFs con URL directa...")
    print("-" * 40)
    
    successful = 0
    failed = 0
    
    for url, filename, subfolder in PDFS_TO_DOWNLOAD:
        if download_pdf(url, filename, subfolder):
            successful += 1
        else:
            failed += 1
    
    print()
    print("=" * 60)
    print(f"✅ Descargas completadas: {successful}")
    print(f"❌ Descargas fallidas: {failed}")
    print("=" * 60)
    
    # Mostrar URLs que requieren descarga manual
    print("\n" + "=" * 60)
    print("📋 PDFs que requieren DESCARGA MANUAL:")
    print("=" * 60)
    
    for territorio, urls in MANUAL_DOWNLOAD_URLS.items():
        print(f"\n🏛️  {territorio.upper()}")
        print("-" * 40)
        for item in urls:
            print(f"   📄 {item['descripcion']}")
            print(f"      URL: {item['url']}")
            print(f"      Nota: {item['nota']}")
        print()
    
    print("\n💡 Después de descargar manualmente, coloca los PDFs en las carpetas correspondientes:")
    print(f"   {DATA_DIR}/Bizkaia/")
    print(f"   {DATA_DIR}/Gipuzkoa/")
    print(f"   {DATA_DIR}/Araba/")
    print(f"   {DATA_DIR}/Navarra/")


if __name__ == "__main__":
    main()
