"""
IAE Lookup Tool for TaxIA

Searches the local JSON catalogue of IAE (Impuesto sobre Actividades Economicas)
epigrafes relevant to digital entrepreneurs, content creators, and tech professionals.

Data source: data/reference/iae_codigos_creadores.json (~30 epigrafes, curated
with DGT binding queries as legal basis where applicable).

Supports keyword search across:
  - descripcion: human-readable activity description
  - notas: DGT references and usage guidance
  - codigo: exact epigrafe number

Query examples:
  - "creador contenido"    → epigrafes 8690
  - "programador"          → epigrafes 763, 773
  - "diseno"               → epigrafes 774, 757
  - "fotografia"           → epigrafe 771
  - "V0773-22"             → epigrafes referencing that DGT query
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# Absolute path resolved at import time — works regardless of cwd
IAE_DATA_PATH = Path(__file__).resolve().parents[3] / "data" / "reference" / "iae_codigos_creadores.json"

IAE_LOOKUP_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_iae",
        "description": (
            "Busca epigrafes IAE (Impuesto sobre Actividades Economicas) por keyword. "
            "Util para recomendar el epigrafe correcto a autonomos y creadores de contenido "
            "digital (YouTubers, podcasters, streamers, programadores, disenadores, "
            "consultores, formadores online, fotografos, traductores, etc.). "
            "Incluye referencias a consultas vinculantes de la DGT cuando existen."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Keyword de busqueda en espanol. Ejemplos: 'creador contenido', "
                        "'programador', 'diseno grafico', 'formacion online', 'fotografia', "
                        "'traductor', 'podcast', 'streamer', 'marketing digital', 'coach'. "
                        "Tambien acepta numeros de epigrafe (ej: '8690', '773')."
                    ),
                },
            },
            "required": ["query"],
        },
    },
}


def _load_iae_data() -> list[dict]:
    """Load IAE catalogue from JSON file. Raises FileNotFoundError if missing."""
    with open(IAE_DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


async def lookup_iae(
    query: str,
    restricted_mode: bool = False,
) -> Dict[str, Any]:
    """
    Search IAE epigrafes by keyword.

    Args:
        query: keyword or epigrafe number to search.
        restricted_mode: if True, return access-restricted error.

    Returns:
        dict with success, count, results (up to 10), and nota with
        the most common epigrafe for digital content creators.
    """
    if restricted_mode:
        return {
            "success": False,
            "error": "restricted",
            "formatted_response": "Esta funcion no esta disponible en tu plan actual.",
        }

    query = query.strip()
    if not query:
        return {
            "success": False,
            "error": "empty_query",
            "formatted_response": "Por favor indica un keyword o codigo IAE a buscar.",
        }

    try:
        data = _load_iae_data()
        query_lower = query.lower()

        # Split multi-word queries: an item matches if ALL tokens appear in its text
        tokens = query_lower.split()
        def _matches(item: dict) -> bool:
            haystack = (
                item["descripcion"].lower()
                + " "
                + item.get("notas", "").lower()
                + " "
                + item["codigo"]
            )
            return all(tok in haystack for tok in tokens)

        results = [item for item in data if _matches(item)]

        # Deduplicate by (codigo, seccion) — the JSON intentionally has two 8690 entries
        # with different descriptions; keep both but avoid exact-duplicate dicts
        seen = set()
        unique_results = []
        for item in results:
            key = (item["codigo"], item["seccion"], item["descripcion"][:40])
            if key not in seen:
                seen.add(key)
                unique_results.append(item)

        logger.info(
            "lookup_iae: query=%r, hits=%d (after dedup: %d)",
            query,
            len(results),
            len(unique_results),
        )

        # Territorial notes injected when query mentions Pais Vasco territories
        pv_keywords = ("pais vasco", "país vasco", "bizkaia", "gipuzkoa", "araba", "alava", "álava", "euskadi")
        notas_territoriales = []
        if any(kw in query_lower for kw in pv_keywords):
            notas_territoriales.append(
                "En Pais Vasco es obligatorio usar software TicketBAI homologado para TODAS las facturas. "
                "Ademas, Bizkaia exige BATUZ (envio continuo de registros de facturacion). "
                "El IAE se presenta ante la respectiva Hacienda Foral, no ante la AEAT."
            )

        nota_base = (
            "El epigrafe 8690 seccion 2 es el mas habitual para creadores de contenido "
            "digital (DGT V0773-22). Si ningun resultado encaja, consulta la clasificacion "
            "IAE oficial del BOE o solicita una consulta vinculante a la DGT."
        )
        nota_final = nota_base
        if notas_territoriales:
            nota_final = nota_base + " | " + " ".join(notas_territoriales)

        return {
            "success": True,
            "query": query,
            "count": len(unique_results),
            "results": unique_results[:10],
            "nota": nota_final,
            "notas_territoriales": notas_territoriales if notas_territoriales else None,
        }

    except FileNotFoundError:
        logger.error("lookup_iae: data file not found at %s", IAE_DATA_PATH)
        return {
            "success": False,
            "error": "data_not_found",
            "formatted_response": "No se pudo cargar el catalogo de epigrafes IAE.",
        }
    except Exception as exc:
        logger.error("lookup_iae error: %s", exc, exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": f"Error al buscar el epigrafe IAE '{query}': {exc}",
        }
