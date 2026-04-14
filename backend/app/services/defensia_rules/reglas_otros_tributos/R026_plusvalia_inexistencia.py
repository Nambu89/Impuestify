"""R026 — plusvalia_inexistencia_incremento (T1B-026).

Regla del Bloque III (otros tributos, bloque Plusvalia Municipal / IIVTNU).
Dispara cuando una liquidacion del Impuesto sobre el Incremento de Valor de
los Terrenos de Naturaleza Urbana grava una transmision en la que, segun las
escrituras publicas de adquisicion y transmision, no existe incremento real
de valor (valor de transmision igual o inferior al de adquisicion).

Invariante #2 (anti-alucinacion): la cita normativa devuelta por la regla es
semantica libre. La cita canonica (art. 104.5 TRLHL, STC 59/2017, RDL 26/2021
y STS 28-2-2024) la resuelve el ``defensia_rag_verifier`` contra el corpus.
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
    "Supuesto de no sujecion al Impuesto sobre el Incremento del Valor de los "
    "Terrenos de Naturaleza Urbana cuando se acredita la inexistencia de "
    "incremento de valor mediante escrituras publicas de adquisicion y "
    "transmision"
)


_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


@regla(
    id="R026",
    tributos=[Tributo.PLUSVALIA.value],
    fases=[
        "LIQUIDACION_FIRME_PLAZO_RECURSO",
        "COMPROBACION_PROPUESTA",
        "COMPROBACION_POST_ALEGACIONES",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    ],
    descripcion=(
        "Plusvalia municipal liquidada sobre transmision con inexistencia de "
        "incremento de valor acreditada en escrituras publicas"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001
) -> ArgumentoCandidato | None:
    """Evalua la regla R026 sobre el expediente.

    Dispara cuando el expediente es de tributo PLUSVALIA y una liquidacion
    provisional o propuesta contiene los dos valores de escritura
    (adquisicion y transmision) y el de transmision es menor o igual al de
    adquisicion. Si falta alguno de los dos valores, la regla no puede
    acreditar la inexistencia de incremento y se abstiene (benefit of the
    doubt).
    """
    if expediente.tributo != Tributo.PLUSVALIA:
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
    if isinstance(tributo_doc, str) and tributo_doc.upper() != "PLUSVALIA":
        return None

    valor_adquisicion = datos.get("valor_adquisicion_escritura")
    valor_transmision = datos.get("valor_transmision_escritura")

    if not isinstance(valor_adquisicion, (int, float)):
        return None
    if not isinstance(valor_transmision, (int, float)):
        return None

    if valor_transmision > valor_adquisicion:
        return None

    perdida = valor_adquisicion - valor_transmision
    if isinstance(perdida, float) and perdida.is_integer():
        perdida = int(perdida)

    return ArgumentoCandidato(
        regla_id="R026",
        descripcion=(
            "Las escrituras publicas acreditan que el valor de transmision "
            "del inmueble es igual o inferior al de adquisicion, por lo que "
            "no existe incremento real de valor susceptible de gravamen por "
            "la plusvalia municipal."
        ),
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo={
            "tipo": "inexistencia_incremento_valor",
            "documento_id": doc.id,
            "tipo_documento": doc.tipo_documento.value,
            "valor_adquisicion": valor_adquisicion,
            "valor_transmision": valor_transmision,
            "perdida": perdida,
        },
        impacto_estimado="alto",
    )
