"""Regla R002 — audiencia_previa_omitida (T1B-002).

Base normativa (research 2026-04-14):
    - Art. 99.8 LGT (Ley 58/2003): admite omitir el tramite de audiencia
      previo solo cuando se suscriban actas con acuerdo o cuando este
      previsto un tramite de alegaciones posterior.
    - Art. 34.1.m) LGT: derecho del contribuyente a ser oido antes de que
      se dicte la resolucion.
    - Art. 82 Ley 39/2015: regulacion general del tramite de audiencia.

Trigger deterministico:
    Esta regla dispara si se detecta alguna de estas dos situaciones en el
    timeline del expediente:

    1. **Salto directo requerimiento -> liquidacion**:
       el expediente contiene un REQUERIMIENTO seguido de una
       LIQUIDACION_PROVISIONAL (o SANCION) sin que entre medias aparezca
       una PROPUESTA_LIQUIDACION y, ademas, el doc resolutorio declara
       `datos.tramite_audiencia_abierto=False`.

    2. **Propuesta modificada sin reabrir plazo**:
       existe una PROPUESTA_LIQUIDACION previa, y la liquidacion posterior
       tiene `datos.propuesta_modificada=True` y
       `datos.nuevo_plazo_alegaciones=False`. La doctrina exige reabrir
       audiencia cuando la Administracion modifica la propuesta.

Excepciones (NO dispara):
    - `datos.acta_con_acuerdo=True` en cualquiera de los docs resolutorios
      (excepcion expresa art. 99.8 LGT).
    - `datos.tramite_audiencia_abierto=True` con alegaciones presentadas
      y sin modificacion posterior de la propuesta.

IMPORTANTE: la cita normativa propuesta es SEMANTICA (descripcion en
lenguaje natural), nunca hardcodeada con numeros de articulo. La
verificacion contra BOE/TEAC es responsabilidad del `defensia_rag_verifier`
en la fase posterior del pipeline.
"""
from __future__ import annotations

from typing import Optional

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import regla


# Tipos de documento considerados "resolutorios" para esta regla: actos
# administrativos finales que requieren audiencia previa.
_DOCS_RESOLUTORIOS = {
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.ACUERDO_IMPOSICION_SANCION,
}


def _tiene_acta_con_acuerdo(exp: ExpedienteEstructurado) -> bool:
    """Devuelve True si cualquier documento del expediente declara acta con acuerdo.

    La excepcion del art. 99.8 LGT opera a nivel de expediente: si existe un
    acta con acuerdo, la omision del tramite de audiencia esta amparada por
    la norma y la regla no debe disparar.
    """
    for doc in exp.documentos:
        if doc.datos.get("acta_con_acuerdo") is True:
            return True
    return False


def _detectar_salto_directo(
    timeline: list,
) -> Optional[tuple[str, str]]:
    """Detecta el salto directo requerimiento -> liquidacion/sancion.

    Recorre el timeline (ya ordenado ASC por fecha_acto) buscando un
    REQUERIMIENTO seguido de un documento resolutorio sin que entre medias
    aparezca una PROPUESTA_LIQUIDACION.

    Devuelve una tupla `(doc_id_resolutorio, motivo)` si detecta el salto,
    o `None` si no encuentra el patron. Solo marca como disparo los
    resolutorios cuyo `datos.tramite_audiencia_abierto` es explicitamente
    `False` — si el campo esta ausente asumimos que no podemos afirmar la
    omision (falsa positivo seguro evitado).
    """
    visto_requerimiento = False
    visto_propuesta = False

    for doc in timeline:
        if doc.tipo_documento == TipoDocumento.REQUERIMIENTO:
            visto_requerimiento = True
            continue
        if doc.tipo_documento == TipoDocumento.PROPUESTA_LIQUIDACION:
            visto_propuesta = True
            continue
        if doc.tipo_documento in _DOCS_RESOLUTORIOS:
            if (
                visto_requerimiento
                and not visto_propuesta
                and doc.datos.get("tramite_audiencia_abierto") is False
            ):
                return (
                    doc.id,
                    "salto directo de requerimiento a resolucion sin tramite "
                    "de audiencia previa",
                )
    return None


def _detectar_propuesta_modificada_sin_reabrir(
    timeline: list,
) -> Optional[tuple[str, str]]:
    """Detecta modificacion de propuesta sin reabrir plazo de alegaciones.

    Busca una PROPUESTA_LIQUIDACION seguida de un documento resolutorio con
    `datos.propuesta_modificada=True` y `datos.nuevo_plazo_alegaciones=False`.
    La doctrina (STS y linea de la Audiencia Nacional) exige reabrir
    audiencia cuando la Administracion altera la propuesta tras alegaciones.
    """
    visto_propuesta = False

    for doc in timeline:
        if doc.tipo_documento == TipoDocumento.PROPUESTA_LIQUIDACION:
            visto_propuesta = True
            continue
        if doc.tipo_documento in _DOCS_RESOLUTORIOS and visto_propuesta:
            if (
                doc.datos.get("propuesta_modificada") is True
                and doc.datos.get("nuevo_plazo_alegaciones") is False
            ):
                return (
                    doc.id,
                    "propuesta de liquidacion modificada sin reabrir plazo "
                    "de alegaciones",
                )
    return None


@regla(
    id="R002",
    tributos=[
        Tributo.IRPF,
        Tributo.IVA,
        Tributo.ISD,
        Tributo.ITP,
        Tributo.PLUSVALIA,
    ],
    fases=[
        Fase.COMPROBACION_POST_ALEGACIONES,
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        Fase.SANCIONADOR_PROPUESTA,
        Fase.SANCIONADOR_IMPUESTA,
        Fase.TEAR_INTERPUESTA,
        Fase.TEAR_AMPLIACION_POSIBLE,
    ],
    descripcion=(
        "Omision del tramite de audiencia previa al contribuyente antes "
        "de dictar liquidacion o sancion, o modificacion de la propuesta "
        "sin reabrir plazo de alegaciones"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado, brief: Brief
) -> Optional[ArgumentoCandidato]:
    """Evalua R002 sobre el expediente y devuelve un candidato si dispara.

    Orden de evaluacion:
        1. Excepcion acta con acuerdo -> None inmediato.
        2. Salto directo requerimiento -> resolutorio sin audiencia.
        3. Propuesta modificada sin reabrir plazo.

    Si ninguno de los patrones coincide, la regla no dispara (retorna None).
    """
    # Excepcion expresa del art. 99.8 LGT: acta con acuerdo ampara la omision.
    if _tiene_acta_con_acuerdo(expediente):
        return None

    timeline = expediente.timeline_ordenado()

    # Patron 1: salto directo requerimiento -> liquidacion sin audiencia.
    salto = _detectar_salto_directo(timeline)
    if salto is not None:
        doc_id, motivo = salto
        return ArgumentoCandidato(
            regla_id="R002",
            descripcion=(
                "El expediente pasa de requerimiento directamente a la "
                "resolucion sin abrir el tramite de audiencia previa al "
                "contribuyente, generando indefension."
            ),
            cita_normativa_propuesta=(
                "Omision del tramite de audiencia previa al contribuyente "
                "antes de dictar la resolucion tributaria"
            ),
            datos_disparo={
                "documento_id": doc_id,
                "motivo": motivo,
                "patron": "salto_directo_requerimiento_resolucion",
            },
            impacto_estimado="anulabilidad del acto por indefension",
        )

    # Patron 2: propuesta modificada sin reabrir plazo de alegaciones.
    modificada = _detectar_propuesta_modificada_sin_reabrir(timeline)
    if modificada is not None:
        doc_id, motivo = modificada
        return ArgumentoCandidato(
            regla_id="R002",
            descripcion=(
                "La propuesta de liquidacion fue modificada por la "
                "Administracion sin reabrir el plazo de alegaciones, "
                "impidiendo al contribuyente pronunciarse sobre los nuevos "
                "elementos introducidos."
            ),
            cita_normativa_propuesta=(
                "Omision de nuevo tramite de audiencia tras modificacion "
                "de la propuesta de resolucion"
            ),
            datos_disparo={
                "documento_id": doc_id,
                "motivo": motivo,
                "patron": "propuesta_modificada_sin_reabrir_plazo",
            },
            impacto_estimado="anulabilidad del acto por indefension",
        )

    return None
