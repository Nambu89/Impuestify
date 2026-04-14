"""R006 — non_bis_in_idem (T1B-006).

Detecta la concurrencia sancionadora entre las infracciones de los articulos
191 LGT (dejar de ingresar) y 194 LGT (solicitud indebida de devoluciones)
sobre un mismo conjunto de hechos. Cuando se detecta, propone un argumento
defensivo basado en el principio `non bis in idem` aplicado al ambito
sancionador tributario.

Contrato de esta regla (invariantes del plan Parte 2):

- La cita normativa propuesta es DESCRIPCION SEMANTICA LIBRE. NO se hardcodea
  ningun articulo ("Art. 180 LGT", "Art. 25 CE", "Ley 58/2003", etc.). La
  resolucion canonica — incluyendo seleccion de articulo aplicable, redaccion
  vigente y referencia BOE — es responsabilidad del RAG verifier posterior.
  El unit test `test_R006_no_hardcodea_cita_normativa` enforce esta regla.
- La regla consume preferentemente el derivado booleano
  `tiene_doble_tipicidad_191_194` que Parte 1 ya calcula en
  `defensia_data_extractor.extract_acuerdo_sancion`. Como fallback (extractores
  legacy o fuentes manuales) tambien acepta una lista `tipos_infraccion` con
  codigos tipo "191", "194" o "194.1".
- Filtrado de fases: solo tiene sentido cuando el expediente esta en sancion
  ya formalizada (propuesta o impuesta) o en recurso contra la misma. La lista
  usa los valores exactos del enum `Fase`.

El argumento devuelto rellena `datos_disparo` con el subset de datos relevantes
para trazabilidad: que doc lo disparo y que infracciones se detectaron. Esto
permite al writer posterior citar fuente sin volver a inspeccionar el expediente.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    DocumentoEstructurado,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
)
from app.services.defensia_rules_engine import regla


# ---------------------------------------------------------------------------
# Helpers de deteccion
# ---------------------------------------------------------------------------

def _normalizar_tipo(valor: Any) -> Optional[str]:
    """Extrae la parte numerica principal de un identificador de infraccion.

    Admite entradas como: "191", "194", "194.1", "Art. 191 LGT", 191 (int).
    Devuelve siempre el codigo base como string ("191", "194") o None si no
    se puede inferir. Cualquier basura se ignora silenciosamente — la regla
    prefiere un falso negativo (no disparar) a un falso positivo (disparar
    en expedientes que no lo merezcan).
    """
    if valor is None:
        return None
    texto = str(valor).strip().lower()
    if not texto:
        return None
    # Extraer el primer numero entero consecutivo.
    digitos = []
    encontrado = False
    for ch in texto:
        if ch.isdigit():
            digitos.append(ch)
            encontrado = True
        elif encontrado:
            break
    if not digitos:
        return None
    return "".join(digitos)


def _tiene_191_y_194(tipos: Iterable[Any]) -> bool:
    """True si la coleccion contiene simultaneamente tipos 191 y 194."""
    normalizados = {n for n in (_normalizar_tipo(t) for t in tipos) if n}
    return "191" in normalizados and "194" in normalizados


def _doc_dispara(doc: DocumentoEstructurado) -> tuple[bool, dict[str, Any]]:
    """Evalua si un documento concreto acredita doble tipicidad 191+194.

    Precedencia de fuentes:
    1. Flag derivado `tiene_doble_tipicidad_191_194` de Parte 1 (preferente).
    2. Lista `tipos_infraccion` con codigos tipo "191"/"194".
    3. Coexistencia de bases `base_sancion_191` y `base_sancion_194` con valor
       no nulo — ultimo recurso para fixtures antiguos.

    Devuelve (dispara, datos_disparo). `datos_disparo` incluye la evidencia
    concreta para trazabilidad aguas abajo.
    """
    datos = doc.datos or {}

    # Path 1: flag derivado — es el contrato oficial con el extractor.
    flag = datos.get("tiene_doble_tipicidad_191_194")
    if flag is True:
        return True, {
            "fuente": "flag_derivado",
            "tiene_doble_tipicidad_191_194": True,
            "doc_id": doc.id,
            "tipo_documento": doc.tipo_documento.value,
        }

    # Path 2: tipos_infraccion explicitos.
    tipos = datos.get("tipos_infraccion")
    if isinstance(tipos, (list, tuple)) and _tiene_191_y_194(tipos):
        return True, {
            "fuente": "tipos_infraccion",
            "tipos_infraccion_detectados": list(tipos),
            "doc_id": doc.id,
            "tipo_documento": doc.tipo_documento.value,
        }

    # Path 3: ambas bases de sancion presentes y no nulas. Solo se considera
    # si `tiene_doble_tipicidad_191_194` NO esta explicitamente en False
    # (el extractor canonico ya lo hubiera marcado True).
    base_191 = datos.get("base_sancion_191")
    base_194 = datos.get("base_sancion_194")
    if (
        flag is not False
        and base_191 not in (None, 0, 0.0)
        and base_194 not in (None, 0, 0.0)
    ):
        return True, {
            "fuente": "bases_sancion",
            "base_sancion_191": base_191,
            "base_sancion_194": base_194,
            "doc_id": doc.id,
            "tipo_documento": doc.tipo_documento.value,
        }

    return False, {}


# ---------------------------------------------------------------------------
# Regla
# ---------------------------------------------------------------------------

_DESCRIPCION_BASE = (
    "Concurrencia sancionadora entre la infraccion por dejar de ingresar "
    "(tipificada en la normativa general tributaria como art. de dejar de "
    "ingresar) y la infraccion por solicitud indebida de devoluciones, "
    "aplicadas sobre un mismo sustrato factico. Esta acumulacion es "
    "incompatible con el principio non bis in idem cuando los hechos base "
    "son los mismos, por lo que procede su revision."
)

# IMPORTANTE: la cita semantica NO contiene numeros de articulo ni referencias
# a cuerpos legales concretos (LGT, CE, Ley 40/2015). El RAG verifier es quien
# resuelve la cita canonica. Ver `test_R006_no_hardcodea_cita_normativa`.
_CITA_SEMANTICA = (
    "Principio non bis in idem en materia sancionadora tributaria: "
    "prohibicion de acumular dos infracciones sobre los mismos hechos cuando "
    "una de ellas ya absorbe el disvalor de la otra"
)


@regla(
    id="R006",
    tributos=["IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"],
    fases=[
        Fase.SANCIONADOR_PROPUESTA.value,
        Fase.SANCIONADOR_IMPUESTA.value,
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Concurrencia de infracciones 191 y 194 sobre los mismos hechos "
        "(non bis in idem)"
    ),
)
def evaluar_R006(
    expediente: ExpedienteEstructurado, brief: Brief,
) -> Optional[ArgumentoCandidato]:
    """Dispara cuando algun documento sancionador acredita doble tipicidad."""
    del brief  # no se usa — la regla es puramente estructural

    # Iteramos solo por los documentos plausibles. Los unicos tipos que pueden
    # fundamentar doble tipicidad 191+194 son los del bloque sancionador.
    tipos_relevantes = {
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        TipoDocumento.PROPUESTA_SANCION,
        TipoDocumento.ACUERDO_INICIO_SANCIONADOR,
    }

    for doc in expediente.documentos:
        if doc.tipo_documento not in tipos_relevantes:
            continue
        dispara, datos_disparo = _doc_dispara(doc)
        if dispara:
            return ArgumentoCandidato(
                regla_id="R006",
                descripcion=_DESCRIPCION_BASE,
                cita_normativa_propuesta=_CITA_SEMANTICA,
                datos_disparo=datos_disparo,
            )

    return None
