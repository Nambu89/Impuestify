"""Detector determinista de fase procesal del expediente.

Algoritmo sin LLM: ordena documentos cronológicamente, identifica el último
acto administrativo y el último escrito del usuario, y aplica reglas de
transición para determinar la fase actual del procedimiento tributario.

Fases soportadas (12 valores del enum Fase, spec §5.2):
- COMPROBACION_REQUERIMIENTO, COMPROBACION_PROPUESTA, COMPROBACION_POST_ALEGACIONES
- LIQUIDACION_FIRME_PLAZO_RECURSO
- SANCIONADOR_INICIADO, SANCIONADOR_PROPUESTA, SANCIONADOR_IMPUESTA
- REPOSICION_INTERPUESTA, TEAR_INTERPUESTA, TEAR_AMPLIACION_POSIBLE
- FUERA_DE_ALCANCE (inspección, apremio, alzada TEAC — no cubierto por v1)
- INDETERMINADA (sin documentos o cadena incoherente)
"""
from __future__ import annotations
from app.models.defensia import (
    ExpedienteEstructurado, TipoDocumento, Fase, DocumentoEstructurado,
)


_FUERA_ALCANCE_TIPOS = {
    TipoDocumento.ACTA_INSPECCION,
    TipoDocumento.PROVIDENCIA_APREMIO,
    TipoDocumento.RESOLUCION_TEAC,
}

_ACTOS_AEAT = {
    TipoDocumento.REQUERIMIENTO,
    TipoDocumento.PROPUESTA_LIQUIDACION,
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.ACUERDO_INICIO_SANCIONADOR,
    TipoDocumento.PROPUESTA_SANCION,
    TipoDocumento.ACUERDO_IMPOSICION_SANCION,
    TipoDocumento.RESOLUCION_TEAR,
}

_ESCRITOS_USUARIO = {
    TipoDocumento.ESCRITO_ALEGACIONES_USUARIO,
    TipoDocumento.ESCRITO_REPOSICION_USUARIO,
    TipoDocumento.ESCRITO_RECLAMACION_TEAR_USUARIO,
}


def detect_fase(expediente: ExpedienteEstructurado) -> tuple[Fase, float]:
    """Detecta la fase procesal del expediente y la confianza [0, 1]."""
    if not expediente.documentos:
        return Fase.INDETERMINADA, 0.0

    for doc in expediente.documentos:
        if doc.tipo_documento in _FUERA_ALCANCE_TIPOS:
            return Fase.FUERA_DE_ALCANCE, 0.99

    timeline = expediente.timeline_ordenado()

    escritos_usuario = [
        d for d in timeline if d.tipo_documento in _ESCRITOS_USUARIO
    ]
    ultimo_escrito_usuario = escritos_usuario[-1] if escritos_usuario else None

    actos_aeat = [d for d in timeline if d.tipo_documento in _ACTOS_AEAT]
    ultimo_acto_aeat = actos_aeat[-1] if actos_aeat else None

    if ultimo_acto_aeat is None:
        return Fase.INDETERMINADA, 0.3

    return _mapear_acto_a_fase(ultimo_acto_aeat, ultimo_escrito_usuario)


def _mapear_acto_a_fase(
    ultimo_acto: DocumentoEstructurado,
    ultimo_escrito_usuario: DocumentoEstructurado | None,
) -> tuple[Fase, float]:
    tipo = ultimo_acto.tipo_documento

    usuario_respondio = (
        ultimo_escrito_usuario is not None
        and ultimo_escrito_usuario.fecha_acto is not None
        and ultimo_acto.fecha_acto is not None
        and ultimo_escrito_usuario.fecha_acto > ultimo_acto.fecha_acto
    )

    if tipo == TipoDocumento.REQUERIMIENTO:
        return Fase.COMPROBACION_REQUERIMIENTO, 0.9

    if tipo == TipoDocumento.PROPUESTA_LIQUIDACION:
        if usuario_respondio:
            return Fase.COMPROBACION_POST_ALEGACIONES, 0.9
        return Fase.COMPROBACION_PROPUESTA, 0.9

    if tipo == TipoDocumento.LIQUIDACION_PROVISIONAL:
        if usuario_respondio:
            subtipo = ultimo_escrito_usuario.tipo_documento
            if subtipo == TipoDocumento.ESCRITO_REPOSICION_USUARIO:
                return Fase.REPOSICION_INTERPUESTA, 0.95
            if subtipo == TipoDocumento.ESCRITO_RECLAMACION_TEAR_USUARIO:
                return Fase.TEAR_AMPLIACION_POSIBLE, 0.95
        return Fase.LIQUIDACION_FIRME_PLAZO_RECURSO, 0.9

    if tipo == TipoDocumento.ACUERDO_INICIO_SANCIONADOR:
        return Fase.SANCIONADOR_INICIADO, 0.9

    if tipo == TipoDocumento.PROPUESTA_SANCION:
        if usuario_respondio:
            return Fase.SANCIONADOR_IMPUESTA, 0.7
        return Fase.SANCIONADOR_PROPUESTA, 0.9

    if tipo == TipoDocumento.ACUERDO_IMPOSICION_SANCION:
        if usuario_respondio:
            subtipo = ultimo_escrito_usuario.tipo_documento
            if subtipo == TipoDocumento.ESCRITO_REPOSICION_USUARIO:
                return Fase.REPOSICION_INTERPUESTA, 0.95
            if subtipo == TipoDocumento.ESCRITO_RECLAMACION_TEAR_USUARIO:
                return Fase.TEAR_AMPLIACION_POSIBLE, 0.95
        return Fase.SANCIONADOR_IMPUESTA, 0.9

    if tipo == TipoDocumento.RESOLUCION_TEAR:
        return Fase.FUERA_DE_ALCANCE, 0.95

    return Fase.INDETERMINADA, 0.5
