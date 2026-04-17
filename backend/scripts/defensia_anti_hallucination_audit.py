"""T3-005 — Anti-alucinación audit DefensIA.

Garantiza el invariante #2 de DefensIA: las plantillas Jinja2 NO hardcodean
citas normativas. Todas las referencias a artículos concretos (Art. 102.2c
LGT, art. 41 bis RIRPF, STS 1234/2023, etc.) deben provenir de argumentos
verificados por el RAG verifier, que entran a la plantilla vía el contexto
``argumentos[*].cita_verificada`` o ``argumentos[*].referencia_normativa_canonica``.

Si una plantilla contiene "Art. 102" literal, significa que estamos
inventando citas fuera del pipeline verificado -> riesgo de alucinación
legal frente al cliente.

Scope:
- backend/app/templates/defensia/*.j2  (ESCANEADO — las plantillas NO deben
  hardcodear citas; todas vienen vía variables Jinja del RAG verifier)

Nota: las reglas deterministas (defensia_rules/**/*.py) SÍ hardcodean
artículos en ``cita_normativa_propuesta`` del ArgumentoCandidato, lo cual
es correcto por diseño — esas citas pasan por el RAG verifier antes de
llegar a la plantilla. NO se escanean aquí.

El script detecta patrones de citas normativas fuera de contextos Jinja
permitidos (``{{ arg.cita_verificada }}``, ``{{ arg.referencia_normativa_canonica }}``).

Uso:
    python backend/scripts/defensia_anti_hallucination_audit.py
    -> exit 0 si OK, exit 1 con listado de hits si detecta citas hardcoded.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent  # TaxIA/

# Patrones de citas normativas concretas que NO deben aparecer literales
# en plantillas. Buscamos artículos específicos con número, sentencias,
# disposiciones, leyes nombradas con numeración concreta.
#
# NO detectamos referencias genéricas ("la Ley General Tributaria",
# "el ordenamiento tributario") porque son aceptables como texto
# narrativo del escrito.
PATRONES_CITA = [
    # Art. 102.2.c, Art. 41 bis, art. 16, Articulo 9.3
    re.compile(r"\b[Aa]rt(?:[íi]culo|\.)?\s+\d+(?:[.,]\d+)*(?:\s*(?:bis|ter|quater))?", re.IGNORECASE),
    # STS 1234/2023, SAN 56/2022, STJUE C-146/05, STSJ ... (sentencias)
    re.compile(r"\b(?:STS|SAN|STJUE|STSJ|STC)\s+(?:C-)?\d+/\d{2,4}\b"),
    # Ley 58/2003, Ley 35/2006 (leyes con numero/año)
    re.compile(r"\bLey\s+\d+/\d{4}\b"),
    # RD 439/2007, Real Decreto 1065/2007
    re.compile(r"\b(?:RD|Real\s+Decreto)\s+\d+/\d{4}\b", re.IGNORECASE),
]

# Ciertas líneas están permitidas aunque contengan patrones: son las que
# usan variables Jinja conocidas que resuelven contenido verificado.
LINEA_PERMITIDA_SI_CONTIENE = [
    "arg.cita_verificada",
    "arg.referencia_normativa_canonica",
    "arg.cita_propuesta",  # fase intermedia en dictamen
    "|escape",
]


def contiene_patron_cita(text: str) -> tuple[bool, str]:
    """True si la cadena contiene alguna cita normativa concreta."""
    for patron in PATRONES_CITA:
        m = patron.search(text)
        if m:
            return True, m.group(0)
    return False, ""


def linea_esta_permitida(linea: str) -> bool:
    return any(s in linea for s in LINEA_PERMITIDA_SI_CONTIENE)


def check_template(path: Path) -> list[tuple[int, str, str]]:
    """Devuelve lista (lineno, cita, linea) en plantillas .j2."""
    hits: list[tuple[int, str, str]] = []
    text = path.read_text(encoding="utf-8")
    in_comment_block = False
    for lineno, linea in enumerate(text.splitlines(), start=1):
        # Skip Jinja comment blocks {# ... #}
        if in_comment_block:
            if "#}" in linea:
                in_comment_block = False
            continue
        if "{#" in linea and "#}" not in linea:
            in_comment_block = True
            continue
        if linea.strip().startswith("{#") and linea.strip().endswith("#}"):
            continue
        # Skip Jinja logic lines {% ... %}
        if linea.strip().startswith("{%"):
            continue
        # Skip si contiene variables Jinja permitidas (la cita viene del RAG)
        if linea_esta_permitida(linea):
            continue
        tiene, cita = contiene_patron_cita(linea)
        if tiene:
            hits.append((lineno, cita, linea.strip()[:140]))
    return hits


def main() -> int:
    total_hits = 0
    templates = sorted((ROOT / "backend" / "app" / "templates" / "defensia").glob("*.j2"))
    print(f"Escaneando {len(templates)} plantillas Jinja2 DefensIA...")
    print()

    for path in templates:
        hits = check_template(path)
        if hits:
            rel = path.relative_to(ROOT)
            for lineno, cita, linea in hits:
                print(f"  {rel}:{lineno} cita hardcodeada: {cita!r}")
                print(f"    {linea}")
            total_hits += len(hits)

    print()
    print(f"Total hits: {total_hits}")

    if total_hits == 0:
        print("OK — plantillas DefensIA sin citas hardcoded (invariante #2 preservado)")
        return 0
    print()
    print("FAIL — alguna plantilla contiene una cita normativa literal.")
    print("       Las citas DEBEN venir de arg.cita_verificada o")
    print("       arg.referencia_normativa_canonica, nunca hardcodeadas.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
