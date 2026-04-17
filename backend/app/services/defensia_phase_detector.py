"""Detector determinista de fase procesal del expediente.

Algoritmo sin LLM: ordena documentos cronológicamente, identifica el último
acto administrativo y el último escrito del usuario, y aplica reglas de
transición para determinar la fase actual del procedimiento tributario.

Fases soportadas (12 valores del enum Fase, spec §5.2):
- COMPROBACION_REQUERIMIENTO, COMPROBACION_PROPUESTA, COMPROBACION_POST_ALEGACIONES
- LIQUIDACION_FIRME_PLAZO_RECURSO
- SANCIONADOR_INICIADO, SANCIONADOR_PROPUESTA, SANCIONADOR_IMPUESTA
- REPOSICION_INTERPUESTA, TEAR_INTERPUESTA, TEAR_AMPLIACION_POSIBLE
- FUERA_DE_ALCANCE (inspección, apremio, alzada TEAC, sentencias — no cubierto por v1)
- INDETERMINADA (sin documentos o cadena incoherente)

Diferenciación TEAR_INTERPUESTA vs TEAR_AMPLIACION_POSIBLE: tras interponer
una reclamación TEAR, durante los primeros 30 días el expediente está en
TEAR_INTERPUESTA (fase activa, ampliación urgente). Pasados 30 días entra en
TEAR_AMPLIACION_POSIBLE (ampliación todavía posible pero menos urgente,
siempre que el TEAR no haya resuelto).
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
from app.models.defensia import (
    ExpedienteEstructurado, TipoDocumento, Fase, DocumentoEstructurado,
)


_TEAR_VENTANA_RECIENTE = timedelta(days=30)


_FUERA_ALCANCE_TIPOS = {
    TipoDocumento.ACTA_INSPECCION,
    TipoDocumento.PROVIDENCIA_APREMIO,
    TipoDocumento.RESOLUCION_TEAC,
    TipoDocumento.SENTENCIA_JUDICIAL,
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


def detect_fase(
    expediente: ExpedienteEstructurado,
    hoy: datetime | None = None,
) -> tuple[Fase, float]:
    """Detecta la fase procesal del expediente y la confianza [0, 1].

    Args:
        expediente: el expediente con documentos ya clasificados y fechados.
        hoy: fecha de referencia para calcular ventanas temporales (TEAR
            reciente vs ampliación posible). Por defecto usa la hora actual UTC.
            Parámetro expuesto para testabilidad determinista.
    """
    if hoy is None:
        hoy = datetime.now(timezone.utc)

    if not expediente.documentos:
        return Fase.INDETERMINADA, 0.0

    for doc in expediente.documentos:
        if doc.tipo_documento in _FUERA_ALCANCE_TIPOS:
            return Fase.FUERA_DE_ALCANCE, 0.99

    # Normaliza fechas naive a UTC para evitar TypeError 'offset-naive
    # vs offset-aware' (Gemini/parseo PDF puede devolver ambos). Copilot
    # review #3 + round 6: NO mutar el expediente recibido — computar
    # sort key con copia normalizada para no crear side effects.
    def _sort_key(doc: DocumentoEstructurado) -> datetime:
        if doc.fecha_acto is None:
            return datetime.max.replace(tzinfo=timezone.utc)
        if doc.fecha_acto.tzinfo is None:
            return doc.fecha_acto.replace(tzinfo=timezone.utc)
        return doc.fecha_acto

    timeline = sorted(expediente.documentos, key=_sort_key)

    escritos_usuario = [
        d for d in timeline if d.tipo_documento in _ESCRITOS_USUARIO
    ]
    ultimo_escrito_usuario = escritos_usuario[-1] if escritos_usuario else None

    actos_aeat = [d for d in timeline if d.tipo_documento in _ACTOS_AEAT]
    ultimo_acto_aeat = actos_aeat[-1] if actos_aeat else None

    if ultimo_acto_aeat is None:
        return Fase.INDETERMINADA, 0.3

    return _mapear_acto_a_fase(ultimo_acto_aeat, ultimo_escrito_usuario, hoy)


def _as_aware_utc(dt: datetime) -> datetime:
    """Devuelve ``dt`` normalizado a timezone-aware UTC.

    Si ``dt`` es naive (tzinfo=None), asume UTC y le adjunta el tz. Si ya es
    aware pero en otra zona, lo convierte a UTC. Previene el
    ``TypeError: can't subtract offset-naive and offset-aware datetimes``
    reportado por Copilot review #3, que rompía ``_es_tear_reciente`` cuando
    llegaban documentos con fecha_acto naive desde Gemini/parseo de PDF.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _es_tear_reciente(
    escrito_tear: DocumentoEstructurado, hoy: datetime
) -> bool:
    """True si el escrito TEAR se presentó hace menos de 30 días.

    Durante esa ventana el expediente está en fase activa TEAR_INTERPUESTA
    (ampliación urgente). Después pasa a TEAR_AMPLIACION_POSIBLE (todavía
    cabe ampliar alegaciones pero el TEAR ya puede estar instruyendo).
    """
    if escrito_tear.fecha_acto is None:
        return False
    return (_as_aware_utc(hoy) - _as_aware_utc(escrito_tear.fecha_acto)) < _TEAR_VENTANA_RECIENTE


def _fase_tras_tear(
    escrito_tear: DocumentoEstructurado, hoy: datetime
) -> Fase:
    return (
        Fase.TEAR_INTERPUESTA
        if _es_tear_reciente(escrito_tear, hoy)
        else Fase.TEAR_AMPLIACION_POSIBLE
    )


def _mapear_acto_a_fase(
    ultimo_acto: DocumentoEstructurado,
    ultimo_escrito_usuario: DocumentoEstructurado | None,
    hoy: datetime,
) -> tuple[Fase, float]:
    tipo = ultimo_acto.tipo_documento

    usuario_respondio = (
        ultimo_escrito_usuario is not None
        and ultimo_escrito_usuario.fecha_acto is not None
        and ultimo_acto.fecha_acto is not None
        and _as_aware_utc(ultimo_escrito_usuario.fecha_acto)
        > _as_aware_utc(ultimo_acto.fecha_acto)
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
                return _fase_tras_tear(ultimo_escrito_usuario, hoy), 0.95
        return Fase.LIQUIDACION_FIRME_PLAZO_RECURSO, 0.9

    if tipo == TipoDocumento.ACUERDO_INICIO_SANCIONADOR:
        return Fase.SANCIONADOR_INICIADO, 0.9

    if tipo == TipoDocumento.PROPUESTA_SANCION:
        # NO saltamos a SANCIONADOR_IMPUESTA aunque el usuario haya respondido:
        # exigiría un ACUERDO_IMPOSICION_SANCION notificado (Copilot review #2).
        # Mientras el último acto administrativo siga siendo una propuesta, la
        # fase correcta es SANCIONADOR_PROPUESTA, independientemente de que el
        # usuario haya presentado alegaciones.
        return Fase.SANCIONADOR_PROPUESTA, 0.9

    if tipo == TipoDocumento.ACUERDO_IMPOSICION_SANCION:
        if usuario_respondio:
            subtipo = ultimo_escrito_usuario.tipo_documento
            if subtipo == TipoDocumento.ESCRITO_REPOSICION_USUARIO:
                return Fase.REPOSICION_INTERPUESTA, 0.95
            if subtipo == TipoDocumento.ESCRITO_RECLAMACION_TEAR_USUARIO:
                return _fase_tras_tear(ultimo_escrito_usuario, hoy), 0.95
        return Fase.SANCIONADOR_IMPUESTA, 0.9

    if tipo == TipoDocumento.RESOLUCION_TEAR:
        return Fase.FUERA_DE_ALCANCE, 0.95

    return Fase.INDETERMINADA, 0.5
