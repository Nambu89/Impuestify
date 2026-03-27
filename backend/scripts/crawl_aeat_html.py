"""
Crawler AEAT paginas HTML con renderizado JavaScript.

Usa Scrapling StealthyFetcher para renderizar JS y extraer contenido
de paginas dinamicas de sede.agenciatributaria.gob.es.

Usage:
    python backend/scripts/crawl_aeat_html.py
    python backend/scripts/crawl_aeat_html.py --dry-run
"""
import argparse
import logging
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent.parent.parent
DOCS_DIR = project_root / "docs" / "AEAT"
BASE_URL = "https://sede.agenciatributaria.gob.es"
RATE_LIMIT = 4  # seconds between requests

PAGES = [
    # (path, filename, subdir)
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/2-impuesto-sobre-actividades-economicas.html",
     "AEAT-IAE-Cap2-Impuesto_Actividades_Economicas.md", "IAE"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/2-impuesto-sobre-actividades-economicas/2_1-modelos.html",
     "AEAT-IAE-Cap2_1-Modelos.md", "IAE"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/2-impuesto-sobre-actividades-economicas/2_1-modelos/2_1_3-clasificacion-actividades.html",
     "AEAT-IAE-Cap2_1_3-Clasificacion_Actividades.md", "IAE"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas.html",
     "AEAT-ActEcon-Cap3-IRPF.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_4-estimacion-directa-normal/3_4_1-calculo-rendimiento-neto.html",
     "AEAT-ActEcon-Cap3_4_1-Calculo_Rendimiento_Neto.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_5-estimacion-directa-simplificada.html",
     "AEAT-ActEcon-Cap3_5-Estimacion_Directa_Simplificada.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_6-estimacion-objetiva.html",
     "AEAT-ActEcon-Cap3_6-Estimacion_Objetiva.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/3-impuesto-sobre-renta-personas-fisicas/3_7-pagos-fraccionados.html",
     "AEAT-ActEcon-Cap3_7-Pagos_Fraccionados.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/5-impuesto-sobre-valor-anadido.html",
     "AEAT-ActEcon-Cap5-IVA.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/5-impuesto-sobre-valor-anadido/5_9-operaciones-intracomunitarias.html",
     "AEAT-ActEcon-Cap5_9-Operaciones_Intracomunitarias.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/5-impuesto-sobre-valor-anadido/5_10-facturas.html",
     "AEAT-ActEcon-Cap5_10-Facturas.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/5-impuesto-sobre-valor-anadido/5_12-veri-factu.html",
     "AEAT-ActEcon-Cap5_12-VeriFactu.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/7-otras-obligaciones-fiscales-retenciones/7_1-cuadro-relacion-tipos-retencion-porcentaje.html",
     "AEAT-ActEcon-Cap7_1-Cuadro_Tipos_Retencion.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/8-declaraciones-informativas.html",
     "AEAT-ActEcon-Cap8-Declaraciones_Informativas.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/folleto-actividades-economicas/1-declaracion-censal.html",
     "AEAT-ActEcon-Cap1-Declaracion_Censal_036.md", "ActividadesEconomicas"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/manual-especifico-personas-discapacidad.html",
     "AEAT-Manual_Discapacidad.md", "Manuales"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/manual-especifico-irpf-2025-personas-anos.html",
     "AEAT-Manual_Mayores_65_IRPF_2025.md", "Manuales"),
    ("/Sede/Ayuda/guia-practica-declaracion-censal.html",
     "AEAT-Guia_Modelo_036.md", "Manuales"),
    ("/Sede/ayuda/manuales-videos-folletos/manuales-practicos/manual-tributacion-no-residentes.html",
     "AEAT-Manual_No_Residentes.md", "Manuales"),
]


def fetch_with_browser(url: str, dest: Path) -> bool:
    """Fetch page with Playwright (real browser JS rendering)."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=30000)
            # Wait for content to render
            page.wait_for_timeout(2000)

            # Try to get main content text
            text = ""
            for selector in ["#contenido", "#textoContenido", ".contenido", "article", "main", "#mainContent"]:
                try:
                    el = page.query_selector(selector)
                    if el:
                        text = el.inner_text()
                        if len(text) > 100:
                            break
                except Exception:
                    continue

            # Fallback: full body
            if len(text) < 100:
                text = page.inner_text("body")

            browser.close()

        # Clean up
        lines = []
        seen = set()
        for line in text.split("\n"):
            line = line.strip()
            if line and len(line) > 2 and line not in seen:
                if any(skip in line.lower() for skip in [
                    "saltar al contenido", "mapa web", "aviso legal",
                    "accesibilidad", "sede electr", "javascript",
                    "cookie", "proteccion de datos", "banner"
                ]):
                    continue
                lines.append(line)
                seen.add(line)
        content = "\n".join(lines)

        if len(content) < 50:
            logger.warning(f"  [!] Too short ({len(content)} chars): {dest.name}")
            return False

        header = f"# {dest.stem.replace('_', ' ')}\n\nFuente: {url}\nDescargado: {time.strftime('%Y-%m-%d')}\n\n---\n\n"
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(header + content, encoding="utf-8")
        logger.info(f"  [+] {dest.name} ({len(content):,} chars)")
        return True
    except Exception as e:
        logger.error(f"  [!] Error: {dest.name}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logger.info("=" * 60)
    logger.info("AEAT HTML Crawler (StealthyFetcher + JS rendering)")
    logger.info(f"Paginas: {len(PAGES)}")
    logger.info("=" * 60)

    stats = {"new": 0, "skipped": 0, "failed": 0}

    for path, filename, subdir in PAGES:
        url = BASE_URL + path
        dest = DOCS_DIR / subdir / filename

        if dest.exists() and dest.stat().st_size > 100:
            logger.info(f"  [=] {filename} (ya existe)")
            stats["skipped"] += 1
            continue

        if args.dry_run:
            logger.info(f"  [DRY] {filename}")
            continue

        if fetch_with_browser(url, dest):
            stats["new"] += 1
        else:
            stats["failed"] += 1
        time.sleep(RATE_LIMIT)

    logger.info(f"\nRESUMEN: Nuevos={stats['new']} | Existentes={stats['skipped']} | Fallidos={stats['failed']}")


if __name__ == "__main__":
    main()
