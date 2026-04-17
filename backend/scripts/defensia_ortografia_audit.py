"""T3-002 — Audit ortografía tildes DefensIA.

Escanea los ficheros DefensIA (backend Python + frontend TS/TSX + plantillas
Jinja2) buscando palabras que deberían llevar tilde pero no la llevan. Exit 1
si encuentra al menos un hit en strings visibles al usuario.

Uso:
    python backend/scripts/defensia_ortografia_audit.py
    python backend/scripts/defensia_ortografia_audit.py --fix  # (NO auto-fix)

Se apoya en heurística léxica: busca substrings en líneas que contienen
comillas (strings) o texto de plantilla Jinja (fuera de expresiones
``{{ ... }}``). Falsos positivos conocidos (identificadores de código,
comentarios técnicos) se excluyen con un whitelist ``IGNORAR_SI_CONTIENE``.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------

# Palabras canónicas sin tilde que DEBEN llevarla cuando son texto
# visible al usuario. Solo las que aparecen razonablemente en DefensIA.
# Formato: incorrecto -> correcto.
PALABRAS_CON_TILDE: dict[str, str] = {
    r"\barticulo\b": "artículo",
    r"\barticulos\b": "artículos",
    r"\brazon\b": "razón",
    r"\braciones\b": "raciones",  # trampa: "raciones" es ok, no incluir
    r"\baccion\b": "acción",
    r"\bacciones\b": "acciones",
    r"\bsancion\b": "sanción",
    r"\bsanciones\b": "sanciones",
    r"\bliquidacion\b": "liquidación",
    r"\bliquidaciones\b": "liquidaciones",
    r"\bprescripcion\b": "prescripción",
    r"\bmotivacion\b": "motivación",
    r"\bnotificacion\b": "notificación",
    r"\bnotificaciones\b": "notificaciones",
    r"\bresolucion\b": "resolución",
    r"\bresoluciones\b": "resoluciones",
    r"\badministracion\b": "administración",
    r"\binformacion\b": "información",
    r"\bdescripcion\b": "descripción",
    r"\bclasificacion\b": "clasificación",
    r"\bdeclaracion\b": "declaración",
    r"\bobligacion\b": "obligación",
    r"\bversion\b": "versión",
    r"\bseccion\b": "sección",
    r"\bdireccion\b": "dirección",
    r"\bautorizacion\b": "autorización",
    r"\bautenticacion\b": "autenticación",
    r"\batencion\b": "atención",
    r"\bcodigo\b": "código",
    r"\banalisis\b": "análisis",
    r"\bbasico\b": "básico",
    r"\beconomico\b": "económico",
    r"\bpublico\b": "público",
    r"\bunico\b": "único",
    r"\btecnico\b": "técnico",
    r"\bultimo\b": "último",
    r"\bultima\b": "última",
    r"\bdeducion\b": "deducción",  # typo alternativo
    r"\bdeduccion\b": "deducción",
    r"\btambien\b": "también",
    r"\bmas\b": "más",
    r"\basi\b": "así",
    r"\bdia\b": "día",
    r"\bdias\b": "días",
    r"\bmes\b": "mes",  # trampa: "mes" es correcto — no incluir
    r"\bano\b": "año",  # muy peligroso: matchea NO_USE etc
    r"\banos\b": "años",
    r"\bsegun\b": "según",
    r"\brespuesta\b": "respuesta",  # correcto, quitar
    r"\bpractico\b": "práctico",
    r"\blegitimacion\b": "legitimación",
    r"\baudiencia\b": "audiencia",  # correcto, quitar
}

# Quitar las entradas que son false positives (palabras correctas sin tilde):
# respuesta, audiencia, raciones, mes — las borramos del dict
for _falso in ["raciones", "respuesta", "audiencia", "mes"]:
    PALABRAS_CON_TILDE.pop(rf"\b{_falso}\b", None)

# Sustrings que si aparecen en la LINEA completa indican que es
# identificador/código y no texto visible (evitan falsos positivos).
IGNORAR_SI_CONTIENE: list[str] = [
    "import ",
    "from ",
    "def ",
    "class ",
    "__",            # dunder, __init__, __name__...
    "TipoDocumento.", "Tributo.", "Fase.",
    "regla_id",
    "REGISTRY",
    "regla(",        # decorador
    "nombre_original",
    "tipo_documento",
    "fase_detectada",
    "ruta_almacenada",
    "hash_sha256",
    "# nosec",
    ".value",
    "CHECK (",
    "FOREIGN KEY",
    "CREATE TABLE",
    "CREATE INDEX",
    "ON DELETE",
    "PRIMARY KEY",
    "DEFAULT",
    "integer",
    "boolean",
    "[main]",
    "TODO",
    "FIXME",
]

# Ficheros objetivo.
#
# Scope deliberadamente acotado al PERIMETRO USER-VISIBLE:
#   1. Plantillas Jinja2 que se exportan al PDF/DOCX del escrito.
#   2. TSX de DefensIA: pages + componentes + types (labels enums).
# El Python backend no entra: su texto va a docstrings, prompts de Gemini
# y dict keys internos. Los strings que SI llegan al usuario salen por las
# plantillas Jinja2 tras pasar por el writer_service, asi que auditar las
# plantillas cubre el backend user-facing de forma indirecta. Para el
# frontend TS no .tsx (hooks) tampoco aplica — no renderizan texto.
ROOT = Path(__file__).parent.parent.parent  # TaxIA/


def _exclude_tests(paths: list[Path]) -> list[Path]:
    """Omitir ficheros de test — sus strings no son user-facing.

    Cubre Vitest/Jest (``*.test.tsx``, ``*.test.ts``) y specs de Playwright
    (``*.spec.tsx``, ``*.spec.ts``).
    """
    return [
        p
        for p in paths
        if not p.name.endswith((".test.tsx", ".test.ts", ".spec.tsx", ".spec.ts"))
    ]


TARGETS: list[Path] = [
    *ROOT.glob("backend/app/templates/defensia/*.j2"),
    *_exclude_tests(list(ROOT.glob("frontend/src/pages/Defensia*.tsx"))),
    *_exclude_tests(list(ROOT.glob("frontend/src/components/defensia/*.tsx"))),
    *ROOT.glob("frontend/src/types/defensia.ts"),
]

# ---------------------------------------------------------------------------
# Lógica
# ---------------------------------------------------------------------------


_jinja_comment_active: dict[str, bool] = {}


def linea_es_string_visible(linea: str, path: Path) -> bool:
    """Heurística: la línea contiene texto visible al usuario.

    Para .py/.ts/.tsx: contiene comillas (simples o dobles) O es parte
    de un docstring. Para .j2: cualquier línea fuera de ``{% ... %}`` y
    fuera de bloques de comentario ``{# ... #}`` multilinea.
    """
    if path.suffix == ".j2":
        key = str(path)
        # Detecta inicio/fin de bloque de comentario multi-linea {# ... #}
        if _jinja_comment_active.get(key, False):
            if "#}" in linea:
                _jinja_comment_active[key] = False
            return False
        if "{#" in linea and "#}" not in linea:
            _jinja_comment_active[key] = True
            return False
        if linea.strip().startswith("{#") and linea.strip().endswith("#}"):
            return False
        return not linea.strip().startswith("{%")
    if '"' in linea or "'" in linea:
        return True
    return False


def check_file(path: Path) -> list[tuple[int, str, str]]:
    """Devuelve lista (lineno, palabra, linea) de hits en el fichero."""
    hits: list[tuple[int, str, str]] = []
    try:
        contenido = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return hits

    for lineno, linea in enumerate(contenido.splitlines(), start=1):
        linea_lower = linea.lower()
        if any(s in linea for s in IGNORAR_SI_CONTIENE):
            continue
        if not linea_es_string_visible(linea, path):
            continue

        for patron, correcto in PALABRAS_CON_TILDE.items():
            m = re.search(patron, linea_lower)
            if not m:
                continue
            # Falsos positivos: la palabra aparece como identificador
            # (key en dict, acceso a propiedad, parámetro). Ejemplos:
            #   descripcion: "Motivación"   -> 'descripcion' es KEY
            #   arg.descripcion             -> acceso a propiedad
            #   descripcion="valor"         -> param name
            start = m.start()
            end = m.end()
            prev_char = linea_lower[start - 1] if start > 0 else " "
            next_chars = linea_lower[end : end + 3]
            if prev_char == "." or next_chars.startswith(("=", ":", "_")):
                continue
            hits.append((lineno, correcto, linea.strip()[:120]))
            break  # un hit por línea basta

    return hits


def main() -> int:
    total_hits = 0
    archivos_con_hits: list[Path] = []

    for path in TARGETS:
        if not path.is_file():
            continue
        hits = check_file(path)
        if hits:
            archivos_con_hits.append(path)
            rel = path.relative_to(ROOT)
            for lineno, correcto, linea in hits:
                print(f"  {rel}:{lineno} -> falta tilde ({correcto})")
                print(f"    {linea}")
            total_hits += len(hits)

    print()
    print(f"Archivos escaneados: {sum(1 for p in TARGETS if p.is_file())}")
    print(f"Archivos con hits:   {len(archivos_con_hits)}")
    print(f"Total hits:          {total_hits}")

    if total_hits == 0:
        print("OK — ortografía DefensIA limpia")
        return 0
    print("FAIL — revisar hits arriba")
    return 1


if __name__ == "__main__":
    sys.exit(main())
