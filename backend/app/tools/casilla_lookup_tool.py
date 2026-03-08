"""
Casilla Lookup Tool for TaxIA

Searches the irpf_casillas table (populated from AEAT diccionarioXSD_2024.properties)
to answer questions about specific Model 100 (IRPF) casilla numbers and their meaning.

Supports two query modes:
  - Numeric query  (e.g. "0505", "505", "casilla 505"):   exact + prefix search by casilla_num
  - Text query     (e.g. "cuota integra", "trabajo"):      LIKE search on description
"""
from typing import Dict, Any
import logging
import re

logger = logging.getLogger(__name__)


async def _get_db():
    from app.database.turso_client import get_db_client
    return await get_db_client()

CASILLA_LOOKUP_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_casilla",
        "description": (
            "Busca informacion sobre casillas del modelo 100 (Declaracion de la Renta / IRPF). "
            "Usa esta herramienta cuando el usuario pregunte que es o que significa una casilla "
            "especifica de la renta (por numero o por concepto). "
            "Puede buscar por numero de casilla (ej: '0505', '505', 'casilla 0020') "
            "o por descripcion/concepto (ej: 'cuota integra estatal', 'rendimientos trabajo', "
            "'pension compensatoria')."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Numero de casilla (ej: '0505', '505') o texto descriptivo a buscar "
                        "(ej: 'cuota integra estatal', 'rendimientos del trabajo'). "
                        "Si el usuario dice 'casilla 505' extrae '505'."
                    ),
                },
            },
            "required": ["query"],
        },
    },
}


def _is_numeric_query(query: str) -> bool:
    """Return True if the query looks like a casilla number (all digits, optional leading zeros)."""
    stripped = query.strip()
    return bool(re.match(r"^\d{1,4}$", stripped))


def _normalize_casilla_num(query: str) -> str:
    """Zero-pad a numeric casilla number to 4 digits."""
    return query.strip().zfill(4)


def _format_results(rows: list[dict], query: str) -> str:
    """Format DB rows into a readable markdown response."""
    if not rows:
        return (
            f"No encontre informacion sobre la casilla o concepto '{query}' "
            f"en el modelo 100 (IRPF 2024). "
            f"Verifica el numero de casilla o reformula la busqueda."
        )

    lines = []
    if len(rows) == 1:
        r = rows[0]
        lines.append(f"**Casilla {r['casilla_num']} — {r['description']}**")
        if r.get("section"):
            lines.append(f"- Seccion: {r['section']}")
    else:
        lines.append(f"**Casillas encontradas para '{query}':**")
        lines.append("")
        for r in rows:
            section_hint = f" _(_{r['section']}_)_" if r.get("section") else ""
            lines.append(f"- **Casilla {r['casilla_num']}**: {r['description']}{section_hint}")

    return "\n".join(lines)


async def lookup_casilla_tool(
    query: str,
    restricted_mode: bool = False,
) -> Dict[str, Any]:
    """
    Look up IRPF casilla(s) by number or description text.

    Args:
        query: casilla number (e.g. "0505") or description text (e.g. "cuota integra")
        restricted_mode: if True, block and return error (content restriction)

    Returns:
        dict with success, results list, and formatted_response string
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
            "formatted_response": "Por favor indica el numero de casilla o concepto a buscar.",
        }

    try:
        db = await _get_db()

        if _is_numeric_query(query):
            # Numeric search: exact match first, then prefix
            padded = _normalize_casilla_num(query)
            result = await db.execute(
                "SELECT casilla_num, description, section, source "
                "FROM irpf_casillas "
                "WHERE casilla_num = ? "
                "ORDER BY casilla_num "
                "LIMIT 10",
                [padded],
            )
            rows = result.rows or []

            if not rows:
                # Prefix fallback (e.g. '05' might match '0500', '0501', ...)
                result = await db.execute(
                    "SELECT casilla_num, description, section, source "
                    "FROM irpf_casillas "
                    "WHERE casilla_num LIKE ? "
                    "ORDER BY casilla_num "
                    "LIMIT 10",
                    [f"{padded}%"],
                )
                rows = result.rows or []
        else:
            # Text search: LIKE on description
            term = f"%{query}%"
            result = await db.execute(
                "SELECT casilla_num, description, section, source "
                "FROM irpf_casillas "
                "WHERE description LIKE ? "
                "ORDER BY casilla_num "
                "LIMIT 10",
                [term],
            )
            rows = result.rows or []

        formatted = _format_results(rows, query)

        logger.info(
            f"lookup_casilla: query={query!r}, mode={'numeric' if _is_numeric_query(query) else 'text'}, "
            f"results={len(rows)}"
        )

        return {
            "success": True,
            "query": query,
            "results": rows,
            "formatted_response": formatted,
        }

    except Exception as exc:
        logger.error(f"lookup_casilla error: {exc}", exc_info=True)
        return {
            "success": False,
            "error": str(exc),
            "formatted_response": f"Error al buscar la casilla '{query}': {exc}",
        }
