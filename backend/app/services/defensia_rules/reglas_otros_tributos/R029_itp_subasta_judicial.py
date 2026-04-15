"""R029 — itp_base_imponible_subasta_judicial (T1B-029).

Regla del Bloque III (ITP). Dispara cuando la liquidacion ITP sobre un
inmueble adjudicado en subasta judicial o en ejecucion hipotecaria aplica el
valor de referencia catastral como base imponible en lugar del precio de
remate efectivamente pagado. Doctrina consolidada del Tribunal Supremo.

Base normativa (resuelta por el RAG verificador, no por la regla):

    - Art. 10 TRLITPAJD (RDL 1/1993) + doctrina reiterada TS Sala 3.ª sobre
      subastas judiciales y valor de adquisicion.
"""
from __future__ import annotations

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import regla


_CITA_SEMANTICA = (
    "Base imponible en transmisiones patrimoniales onerosas derivadas de "
    "subastas judiciales y adjudicaciones en ejecuciones hipotecarias fijada "
    "en el precio de remate efectivamente pagado, conforme a la doctrina "
    "jurisprudencial consolidada del Tribunal Supremo"
)


_ORIGENES_SUBASTA = (
    "subasta_judicial",
    "ejecucion_hipotecaria",
    "adjudicacion_judicial",
)


_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


@regla(
    id="R029",
    tributos=[Tributo.ITP.value],
    fases=[
        "LIQUIDACION_FIRME_PLAZO_RECURSO",
        "COMPROBACION_PROPUESTA",
        "COMPROBACION_POST_ALEGACIONES",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    ],
    descripcion=(
        "Base imponible ITP en subasta judicial o ejecucion hipotecaria debe "
        "ser el precio de remate, no el valor de referencia catastral"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001
) -> ArgumentoCandidato | None:
    """Evalua la regla R029 sobre el expediente.

    Requisitos para disparar:

    1. El tributo es ITP.
    2. El expediente contiene una liquidacion/propuesta con el origen de
       adquisicion en ``_ORIGENES_SUBASTA`` (subasta judicial, ejecucion
       hipotecaria o adjudicacion judicial analoga).
    3. La base imponible aplicada por AEAT es estrictamente superior al
       precio de remate efectivamente pagado.
    """
    if expediente.tributo != Tributo.ITP:
        return None

    doc = next(
        (
            d
            for d in expediente.documentos
            if d.tipo_documento in _TIPOS_LIQUIDACION
        ),
        None,
    )
    if doc is None:
        return None

    datos = doc.datos or {}

    tributo_doc = datos.get("tributo")
    if isinstance(tributo_doc, str) and tributo_doc.upper() != "ITP":
        return None

    origen = datos.get("origen_adquisicion")
    if not isinstance(origen, str):
        return None
    if origen.lower() not in _ORIGENES_SUBASTA:
        return None

    precio_remate = datos.get("precio_remate")
    base_aplicada = datos.get("base_imponible_aplicada_por_aeat")

    if not isinstance(precio_remate, (int, float)):
        return None
    if not isinstance(base_aplicada, (int, float)):
        return None

    if base_aplicada <= precio_remate:
        return None

    diferencia = base_aplicada - precio_remate
    if isinstance(diferencia, float) and diferencia.is_integer():
        diferencia = int(diferencia)

    return ArgumentoCandidato(
        regla_id="R029",
        descripcion=(
            "La liquidacion ITP sobre un inmueble adjudicado en subasta "
            "judicial o ejecucion hipotecaria ha tomado como base imponible "
            "el valor de referencia catastral en lugar del precio de remate "
            "efectivamente pagado, contra doctrina jurisprudencial "
            "consolidada."
        ),
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo={
            "tipo": "base_imponible_subasta_judicial",
            "documento_id": doc.id,
            "tipo_documento": doc.tipo_documento.value,
            "origen_adquisicion": origen.lower(),
            "precio_remate": precio_remate,
            "base_imponible_aplicada_por_aeat": base_aplicada,
            "diferencia": diferencia,
        },
        impacto_estimado="alto",
    )
