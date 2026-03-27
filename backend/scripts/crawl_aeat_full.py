"""
Crawler exhaustivo de la web de AEAT.

Descarga todos los manuales practicos, guias y documentos fiscales
relevantes de sede.agenciatributaria.gob.es.

Usa Scrapling para anti-bot y rate limiting.
Respeta robots.txt (solo bloquea /NoIx/ y *_NoIx.pdf).

Usage:
    python backend/scripts/crawl_aeat_full.py                    # Descargar todo
    python backend/scripts/crawl_aeat_full.py --dry-run           # Solo listar URLs
    python backend/scripts/crawl_aeat_full.py --only-pdfs         # Solo PDFs
    python backend/scripts/crawl_aeat_full.py --only-html         # Solo paginas HTML
"""
import asyncio
import argparse
import hashlib
import logging
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

# Fix Windows encoding
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))
project_root = backend_dir.parent

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

BASE_URL = "https://sede.agenciatributaria.gob.es"
DOCS_DIR = project_root / "docs" / "AEAT"

# PDFs prioritarios de la AEAT (manuales 2025 + guias clave)
PRIORITY_PDFS = [
    # --- IRPF 2025 ---
    ("/static_files/Sede/Biblioteca/Manual/Practicos/IRPF/IRPF-2025/ManualRenta2025Parte1_es_es.pdf",
     "AEAT-Manual_Renta_2025_Parte1.pdf", "Renta-2025"),
    ("/static_files/Sede/Biblioteca/Manual/Practicos/IRPF/IRPF-2025-Deducciones-autonomicas/ManualRenta2025Parte2_es_es.pdf",
     "AEAT-Manual_Renta_2025_Parte2_Deducciones_Autonomicas.pdf", "Renta-2025"),
    # --- IVA 2025 ---
    ("/static_files/Sede/Biblioteca/Manual/Practicos/IVA/Manual_IVA_2025.pdf",
     "AEAT-Manual_IVA_2025.pdf", "IVA"),
    # --- Patrimonio 2025 ---
    ("/static_files/Sede/Biblioteca/Manual/Practicos/Patrimonio/Patrimonio-2025/ManualPatrimonio2025_es_es.pdf",
     "AEAT-Manual_Patrimonio_2025.pdf", "Patrimonio"),
    # --- Sociedades 2024 ---
    ("/static_files/Sede/Biblioteca/Manual/Practicos/Sociedades/Manual_Sociedades_2024.pdf",
     "AEAT-Manual_Sociedades_2024.pdf", "Sociedades"),
    # --- VeriFactu ---
    ("/static_files/Sede/Biblioteca/Manual/Practicos/Manual_facturacion/Manual_Usuario_Verifactu_Accesible.pdf",
     "AEAT-Guia_VeriFactu.pdf", "VeriFactu"),
    # --- Facturacion ---
    ("/static_files/Sede/Biblioteca/Manual/Practicos/Facturacion_y_libros_registro_IVA/manual_facturacion_2011_es_es.pdf",
     "AEAT-Manual_Facturacion_LibrosRegistro_IVA.pdf", "Facturacion"),
]

# Paginas HTML con contenido fiscal valioso (se guardaran como .md)
PRIORITY_HTML_PAGES = [
    # Manual de Actividades Economicas - capitulos clave
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/2-impuesto-sobre-actividades-economicas.html",
     "AEAT-IAE-Cap2-Impuesto_Actividades_Economicas.md", "IAE"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/2-impuesto-sobre-actividades-economicas/2_1-modelos.html",
     "AEAT-IAE-Cap2_1-Modelos.md", "IAE"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/2-impuesto-sobre-actividades-economicas/2_1-modelos/2_1_3-clasificacion-actividades.html",
     "AEAT-IAE-Cap2_1_3-Clasificacion_Actividades.md", "IAE"),
    # IRPF actividades economicas
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas.html",
     "AEAT-ActEcon-Cap3-IRPF.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_4-estimacion-directa-normal.html",
     "AEAT-ActEcon-Cap3_4-Estimacion_Directa_Normal.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_4-estimacion-directa-normal/3_4_1-calculo-rendimiento-neto.html",
     "AEAT-ActEcon-Cap3_4_1-Calculo_Rendimiento_Neto.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_5-estimacion-directa-simplificada.html",
     "AEAT-ActEcon-Cap3_5-Estimacion_Directa_Simplificada.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_6-estimacion-objetiva.html",
     "AEAT-ActEcon-Cap3_6-Estimacion_Objetiva.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_7-pagos-fraccionados.html",
     "AEAT-ActEcon-Cap3_7-Pagos_Fraccionados.md", "ActividadesEconomicas"),
    # IVA actividades economicas
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/5-impuesto-sobre-valor-anadido.html",
     "AEAT-ActEcon-Cap5-IVA.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/5-impuesto-sobre-valor-anadido/5_9-operaciones-intracomunitarias.html",
     "AEAT-ActEcon-Cap5_9-Operaciones_Intracomunitarias.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/5-impuesto-sobre-valor-anadido/5_10-facturas.html",
     "AEAT-ActEcon-Cap5_10-Facturas.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/5-impuesto-sobre-valor-anadido/5_12-veri-factu.html",
     "AEAT-ActEcon-Cap5_12-VeriFactu.md", "ActividadesEconomicas"),
    # Retenciones
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/7-otras-obligaciones-fiscales-retenciones.html",
     "AEAT-ActEcon-Cap7-Retenciones.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/7-otras-obligaciones-fiscales-retenciones/7_1-cuadro-relacion-tipos-retencion-porcentaje.html",
     "AEAT-ActEcon-Cap7_1-Cuadro_Tipos_Retencion.md", "ActividadesEconomicas"),
    # Declaraciones informativas
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/8-declaraciones-informativas.html",
     "AEAT-ActEcon-Cap8-Declaraciones_Informativas.md", "ActividadesEconomicas"),
    # Declaracion censal
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/1-declaracion-censal.html",
     "AEAT-ActEcon-Cap1-Declaracion_Censal_036.md", "ActividadesEconomicas"),
    # Manual discapacidad
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/manual-especifico-personas-discapacidad.html",
     "AEAT-Manual_Discapacidad.md", "Manuales"),
    # Manual mayores 65
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/manual-especifico-irpf-2025-personas-anos.html",
     "AEAT-Manual_Mayores_65_IRPF_2025.md", "Manuales"),
    # Guia modelo 036
    ("/Sede/Ayuda/guia-practica-declaracion-censal.html",
     "AEAT-Guia_Modelo_036.md", "Manuales"),
    # No residentes
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/manual-tributacion-no-residentes.html",
     "AEAT-Manual_No_Residentes.md", "Manuales"),
]

RATE_LIMIT_SECONDS = 3  # seconds between requests
REQUEST_TIMEOUT = 60


def is_blocked_by_robots(path: str) -> bool:
    """Check if path is blocked by AEAT robots.txt."""
    blocked = ["/Sede/NoIx/", "/static_files/Sede/NoIx/", "/static_files/AEAT/NoIx/",
               "/static_files/AEAT_Sede/NoIx/", "/static_files/common/NoIx/"]
    if any(path.startswith(b) for b in blocked):
        return True
    if path.endswith("_NoIx.pdf"):
        return True
    return False


def download_pdf(url: str, dest: Path) -> bool:
    """Download a PDF file."""
    try:
        from scrapling.fetchers import Fetcher
        fetcher = Fetcher()
        response = fetcher.get(url, timeout=REQUEST_TIMEOUT)
        if response.status == 200:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(response.body)
            size_kb = len(response.body) / 1024
            logger.info(f"  [+] {dest.name} ({size_kb:.0f} KB)")
            return True
        else:
            logger.warning(f"  [X] HTTP {response.status}: {dest.name}")
            return False
    except Exception as e:
        logger.error(f"  [!] Error downloading {dest.name}: {e}")
        return False


def fetch_html_as_markdown(url: str, dest: Path) -> bool:
    """Fetch HTML page and save as markdown."""
    try:
        from scrapling.fetchers import Fetcher
        fetcher = Fetcher()
        response = fetcher.get(url, timeout=REQUEST_TIMEOUT)
        if response.status != 200:
            logger.warning(f"  [X] HTTP {response.status}: {dest.name}")
            return False

        # Extract main content using CSS selectors
        # AEAT uses <div id="contenido"> or similar
        content_el = response.css("#contenido") or response.css(".contenido") or response.css("main")
        if content_el:
            text = content_el[0].text
        else:
            text = response.text

        # Clean up
        lines = []
        for line in text.split("\n"):
            line = line.strip()
            if line and len(line) > 2:
                lines.append(line)
        content = "\n".join(lines)

        if len(content) < 100:
            logger.warning(f"  [!] Too short ({len(content)} chars): {dest.name}")
            return False

        # Add source header
        header = f"# {dest.stem.replace('_', ' ')}\n\nFuente: {url}\nDescargado: {time.strftime('%Y-%m-%d')}\n\n---\n\n"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(header + content, encoding="utf-8")
        logger.info(f"  [+] {dest.name} ({len(content):,} chars)")
        return True
    except Exception as e:
        logger.error(f"  [!] Error fetching {dest.name}: {e}")
        return False


def file_already_exists(dest: Path) -> bool:
    """Check if file exists and is not empty."""
    return dest.exists() and dest.stat().st_size > 100


def main():
    parser = argparse.ArgumentParser(description="Crawl AEAT for fiscal documents")
    parser.add_argument("--dry-run", action="store_true", help="Only list URLs without downloading")
    parser.add_argument("--only-pdfs", action="store_true", help="Only download PDFs")
    parser.add_argument("--only-html", action="store_true", help="Only fetch HTML pages")
    parser.add_argument("--force", action="store_true", help="Re-download existing files")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("AEAT Full Crawler — sede.agenciatributaria.gob.es")
    logger.info("=" * 60)

    stats = {"new": 0, "skipped": 0, "failed": 0}

    # === PHASE 1: Priority PDFs ===
    if not args.only_html:
        logger.info(f"\n--- FASE 1: PDFs Prioritarios ({len(PRIORITY_PDFS)} archivos) ---")
        for path, filename, subdir in PRIORITY_PDFS:
            url = BASE_URL + path
            dest = DOCS_DIR / subdir / filename

            if is_blocked_by_robots(path):
                logger.info(f"  [BLOCKED] {filename} (robots.txt)")
                continue

            if file_already_exists(dest) and not args.force:
                logger.info(f"  [=] {filename} (ya existe)")
                stats["skipped"] += 1
                continue

            if args.dry_run:
                logger.info(f"  [DRY] {filename} <- {url}")
                continue

            if download_pdf(url, dest):
                stats["new"] += 1
            else:
                stats["failed"] += 1
            time.sleep(RATE_LIMIT_SECONDS)

    # === PHASE 2: HTML Pages ===
    if not args.only_pdfs:
        logger.info(f"\n--- FASE 2: Paginas HTML ({len(PRIORITY_HTML_PAGES)} paginas) ---")
        for path, filename, subdir in PRIORITY_HTML_PAGES:
            url = BASE_URL + path
            dest = DOCS_DIR / subdir / filename

            if is_blocked_by_robots(path):
                logger.info(f"  [BLOCKED] {filename} (robots.txt)")
                continue

            if file_already_exists(dest) and not args.force:
                logger.info(f"  [=] {filename} (ya existe)")
                stats["skipped"] += 1
                continue

            if args.dry_run:
                logger.info(f"  [DRY] {filename} <- {url}")
                continue

            if fetch_html_as_markdown(url, dest):
                stats["new"] += 1
            else:
                stats["failed"] += 1
            time.sleep(RATE_LIMIT_SECONDS)

    # === Summary ===
    logger.info(f"\n{'=' * 60}")
    logger.info(f"RESUMEN: Nuevos={stats['new']} | Ya existentes={stats['skipped']} | Fallidos={stats['failed']}")
    logger.info(f"Pendiente: ingestar nuevos docs con ingest_documents.py + rebuild_fts5.py")


if __name__ == "__main__":
    main()
