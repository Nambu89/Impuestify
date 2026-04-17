"""R028 — plusvalia_prescripcion_o_notificacion (T1B-028).

Regla del Bloque III (otros tributos, bloque Plusvalia Municipal / IIVTNU).
Dispara cuando el Ayuntamiento notifica la liquidacion de plusvalia municipal
fuera del plazo de 4 anos desde el devengo del impuesto (fallecimiento en
transmisiones mortis causa o fecha de escritura en inter vivos) sin que haya
existido una interrupcion valida del plazo de prescripcion.

Base normativa (la resuelve el RAG verificador, no la regla — invariante #2):

    - Arts. 66-68 LGT aplicables a tributos locales por remision del art. 12
      TRLHL (Real Decreto Legislativo 2/2004).
    - STS Sala 3.ª 28-2-2024: admite nulidad radical de liquidaciones firmes
      dictadas fuera del plazo de 4 anos desde el devengo.
"""
from __future__ import annotations

from datetime import date, datetime

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import regla


_CITA_SEMANTICA = (
    "Prescripcion del derecho del Ayuntamiento a liquidar el Impuesto sobre "
    "el Incremento del Valor de los Terrenos de Naturaleza Urbana por "
    "transcurso del plazo de cuatro anos desde el devengo sin acto "
    "interruptivo valido"
)


_PLAZO_PRESCRIPCION_ANOS = 4


_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


def _parse_fecha(valor) -> date | None:
    """Parsea valor a ``date``. Acepta ``date``, ``datetime``, string ISO."""
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return datetime.fromisoformat(valor).date()
        except ValueError:
            return None
    return None


@regla(
    id="R028",
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
        "Plusvalia municipal liquidada fuera del plazo de 4 anos desde el "
        "devengo sin interrupcion valida del plazo de prescripcion"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001
) -> ArgumentoCandidato | None:
    """Evalua la regla R028 sobre el expediente.

    Calcula el tiempo transcurrido entre ``fecha_devengo`` y
    ``fecha_notificacion_liquidacion`` usando computo fecha a fecha (limite =
    devengo + 4 anos). Dispara cuando la notificacion es estrictamente
    posterior al limite y no hubo interrupcion previa valida.
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

    if datos.get("hubo_interrupcion") is True:
        return None

    fecha_devengo = _parse_fecha(datos.get("fecha_devengo"))
    fecha_notif = _parse_fecha(datos.get("fecha_notificacion_liquidacion"))
    if fecha_devengo is None or fecha_notif is None:
        return None

    try:
        limite_prescripcion = date(
            fecha_devengo.year + _PLAZO_PRESCRIPCION_ANOS,
            fecha_devengo.month,
            fecha_devengo.day,
        )
    except ValueError:
        return None

    if fecha_notif <= limite_prescripcion:
        return None

    anos_transcurridos = fecha_notif.year - fecha_devengo.year
    if (fecha_notif.month, fecha_notif.day) < (
        fecha_devengo.month,
        fecha_devengo.day,
    ):
        anos_transcurridos -= 1

    dias_exceso = (fecha_notif - limite_prescripcion).days

    return ArgumentoCandidato(
        regla_id="R028",
        descripcion=(
            "El Ayuntamiento ha notificado la liquidacion de la plusvalia "
            "municipal transcurrido el plazo de cuatro anos desde el devengo "
            "del impuesto, sin acto interruptivo valido previo, por lo que "
            "el derecho a liquidar esta prescrito."
        ),
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo={
            "tipo": "prescripcion_plusvalia",
            "documento_id": doc.id,
            "tipo_documento": doc.tipo_documento.value,
            "fecha_devengo": fecha_devengo.isoformat(),
            "fecha_notificacion_liquidacion": fecha_notif.isoformat(),
            "anos_transcurridos": anos_transcurridos,
            "dias_exceso_sobre_limite": dias_exceso,
            "limite_prescripcion": limite_prescripcion.isoformat(),
        },
        impacto_estimado="alto",
    )
