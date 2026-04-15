"""R030 — iva_recargo_equivalencia (T1B-030).

Regla del Bloque III (IVA). Dispara cuando AEAT regulariza IVA a un
comerciante minorista persona fisica o entidad en regimen de atribucion de
rentas (EARE) que deberia estar obligatoriamente en el regimen especial del
recargo de equivalencia, en lugar de liberarle de liquidar el impuesto ante
la Administracion tributaria.

Base normativa (resuelta por el RAG verificador, no por la regla):

    - Arts. 148 a 163 LIVA. Tipos de recargo: 5,2 % (general), 1,4 %
      (reducido), 0,5 % (superreducido), 1,75 % (tabaco).
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
    "Regimen especial obligatorio del recargo de equivalencia para "
    "comerciantes minoristas personas fisicas o entidades en regimen de "
    "atribucion de rentas, que libera al obligado de liquidar el Impuesto "
    "sobre el Valor Anadido ante la Administracion tributaria"
)


_TIPOS_OBLIGADO_SUJETOS = (
    "persona_fisica_minorista",
    "entidad_atribucion_rentas_minorista",
)


_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


@regla(
    id="R030",
    tributos=[Tributo.IVA.value],
    fases=[
        "LIQUIDACION_FIRME_PLAZO_RECURSO",
        "COMPROBACION_PROPUESTA",
        "COMPROBACION_POST_ALEGACIONES",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    ],
    descripcion=(
        "IVA regularizado a comerciante minorista persona fisica o EARE que "
        "deberia estar en regimen obligatorio de recargo de equivalencia"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001
) -> ArgumentoCandidato | None:
    """Evalua la regla R030 sobre el expediente.

    Dispara cuando el obligado tributario es persona fisica minorista o
    entidad en regimen de atribucion de rentas dedicada al comercio
    minorista, cumple los requisitos del regimen y AEAT le regulariza IVA en
    lugar de reconocerle el recargo de equivalencia.
    """
    if expediente.tributo != Tributo.IVA:
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
    if isinstance(tributo_doc, str) and tributo_doc.upper() != "IVA":
        return None

    tipo_obligado = datos.get("tipo_obligado")
    if not isinstance(tipo_obligado, str):
        return None
    if tipo_obligado.lower() not in _TIPOS_OBLIGADO_SUJETOS:
        return None

    aeat_regulariza = bool(datos.get("aeat_regulariza_iva", False))
    recargo_aplicado = bool(datos.get("recargo_equivalencia_aplicado", False))
    cumple_requisitos = bool(datos.get("cumple_requisitos_minorista", True))

    if not aeat_regulariza:
        return None
    if recargo_aplicado:
        return None
    if not cumple_requisitos:
        return None

    return ArgumentoCandidato(
        regla_id="R030",
        descripcion=(
            "La Administracion ha regularizado el Impuesto sobre el Valor "
            "Anadido a un comerciante minorista persona fisica o entidad en "
            "regimen de atribucion de rentas, cuando por imperativo legal "
            "deberia estar incluido obligatoriamente en el regimen especial "
            "del recargo de equivalencia, quedando liberado de liquidar el "
            "impuesto ante la Administracion."
        ),
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo={
            "tipo": "regimen_recargo_equivalencia_no_reconocido",
            "documento_id": doc.id,
            "tipo_documento": doc.tipo_documento.value,
            "tipo_obligado": tipo_obligado.lower(),
            "cumple_requisitos_minorista": cumple_requisitos,
        },
        impacto_estimado="alto",
    )
