"""Regla R009 — caducidad_sancionador (T1B-009).

Base normativa (research 2026-04-14):
    - Art. 211.2 LGT (Ley 58/2003): el procedimiento sancionador debera
      concluir en el plazo maximo de SEIS MESES desde la notificacion del
      acuerdo de iniciacion. Transcurrido dicho plazo sin que se haya
      notificado resolucion expresa, se entendera caducado.
    - Art. 211.4 LGT: la caducidad impide el inicio de un nuevo
      procedimiento sancionador sobre los mismos hechos.
    - Doctrina reiterada del Tribunal Supremo y TEAC sobre el computo
      estricto de los 6 meses (fecha a fecha, meses calendario).

Trigger deterministico:
    Esta regla dispara cuando existe un documento
    ``ACUERDO_IMPOSICION_SANCION`` en cuyo ``datos`` aparecen las claves
    ``fecha_inicio_sancionador`` y ``fecha_notificacion_sancion`` y el
    numero de dias transcurridos entre una y otra supera el plazo de 6
    meses calendario calculado con ``dateutil.relativedelta``.

    Se prefiere ``relativedelta(months=6)`` sobre una aproximacion de
    ``timedelta(days=183)`` porque el plazo legal del art. 211.2 LGT se
    computa de fecha a fecha — el dia 2025-01-15 da limite 2025-07-15,
    no 2025-07-17.

Exclusiones (NO dispara):
    - Expediente en fase ajena al sancionador (ej. `LIQUIDACION_FIRME_*`).
      El filtrado lo aplica el motor a partir del atributo `fases=[...]`
      de este decorador.
    - Fechas dentro del plazo de 6 meses (inclusive el dia limite exacto).
    - Ausencia de alguna de las dos fechas (extraccion incompleta) —
      en ese caso la regla devuelve ``None`` en vez de alucinar un
      disparo con datos parciales.

Invariante #2 del plan Parte 2:
    La cita normativa es SEMANTICA. Nunca hardcodeamos "Art. 211.2 LGT"
    en el codigo de la regla: la cita canonica la resuelve posteriormente
    el ``defensia_rag_verifier``. Aqui solo describimos el fenomeno
    juridico ("caducidad del procedimiento sancionador por exceso del
    plazo maximo legal de tramitacion").
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from dateutil.relativedelta import relativedelta

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import regla


# Meses calendario que marcan el plazo maximo legal del procedimiento
# sancionador tributario (art. 211.2 LGT). Se expresa como constante local
# para evitar numeros magicos en la logica de la regla.
_PLAZO_MAX_MESES_SANCIONADOR = 6


def _parse_fecha(valor) -> Optional[datetime]:
    """Convierte `valor` a datetime naive (sin tz) para calculos de plazo.

    Acepta:
        - ``datetime`` (devuelve tal cual, stripeando tzinfo para evitar
          mezclar naive/aware en el calculo).
        - ``str`` en formato ISO ``YYYY-MM-DD`` o ``YYYY-MM-DDTHH:MM:SS``.
        - ``None`` -> ``None`` (extraccion incompleta, la regla abortara).

    Cualquier otro formato devuelve ``None`` para evitar crashes — una
    regla defectuosa NO debe poder tumbar el motor (el ``evaluar()`` del
    engine ya captura excepciones, pero aqui somos defensivos).
    """
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.replace(tzinfo=None)
    if isinstance(valor, str):
        try:
            dt = datetime.fromisoformat(valor)
            return dt.replace(tzinfo=None)
        except ValueError:
            return None
    return None


def _calcular_dias_exceso(
    fecha_inicio: datetime, fecha_fin: datetime
) -> int:
    """Devuelve dias transcurridos entre `fecha_fin` y el limite legal.

    El limite legal es ``fecha_inicio + relativedelta(months=6)``. Si la
    diferencia es negativa (o cero) el procedimiento esta dentro de plazo
    y la funcion devuelve ``0`` (la regla NO dispara).
    """
    limite = fecha_inicio + relativedelta(months=_PLAZO_MAX_MESES_SANCIONADOR)
    delta = fecha_fin - limite
    dias = delta.days
    return dias if dias > 0 else 0


def _buscar_documento_sancion(
    expediente: ExpedienteEstructurado,
) -> Optional[object]:
    """Localiza el primer `ACUERDO_IMPOSICION_SANCION` del expediente.

    Si hay varios acuerdos de imposicion (caso raro en expedientes reales
    pero posible con expedientes refundidos), devolvemos el primero del
    timeline ordenado — el mas antiguo, que es el relevante a efectos de
    caducidad del procedimiento original.
    """
    for doc in expediente.timeline_ordenado():
        if doc.tipo_documento == TipoDocumento.ACUERDO_IMPOSICION_SANCION:
            return doc
    return None


@regla(
    id="R009",
    tributos=[
        Tributo.IRPF,
        Tributo.IVA,
        Tributo.ISD,
        Tributo.ITP,
        Tributo.PLUSVALIA,
    ],
    fases=[
        Fase.SANCIONADOR_INICIADO,
        Fase.SANCIONADOR_PROPUESTA,
        Fase.SANCIONADOR_IMPUESTA,
        Fase.REPOSICION_INTERPUESTA,
        Fase.TEAR_INTERPUESTA,
        Fase.TEAR_AMPLIACION_POSIBLE,
    ],
    descripcion=(
        "Caducidad del procedimiento sancionador por exceso del plazo "
        "máximo legal de seis meses de tramitación, con cómputo de fecha "
        "a fecha"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado, brief: Brief
) -> Optional[ArgumentoCandidato]:
    """Evalua R009 sobre el expediente y devuelve un candidato si dispara.

    Algoritmo:
        1. Localizar el documento ACUERDO_IMPOSICION_SANCION.
        2. Leer ``datos.fecha_inicio_sancionador`` y
           ``datos.fecha_notificacion_sancion``; abortar si falta alguna.
        3. Calcular ``dias_exceso`` usando meses calendario reales.
        4. Si ``dias_exceso > 0`` -> emitir ArgumentoCandidato.
           En caso contrario -> ``None``.

    Datos emitidos en ``datos_disparo`` (los consume el writer + el RAG
    verificador aguas abajo):
        - ``documento_id`` del acuerdo analizado.
        - ``fecha_inicio_sancionador`` ISO.
        - ``fecha_notificacion_sancion`` ISO.
        - ``plazo_maximo_meses`` (6, constante).
        - ``dias_exceso`` (int > 0 dias sobre el limite legal).
    """
    doc = _buscar_documento_sancion(expediente)
    if doc is None:
        return None

    fecha_inicio = _parse_fecha(doc.datos.get("fecha_inicio_sancionador"))
    fecha_fin = _parse_fecha(doc.datos.get("fecha_notificacion_sancion"))
    if fecha_inicio is None or fecha_fin is None:
        # Extraccion incompleta: la regla no puede pronunciarse sin datos.
        return None

    dias_exceso = _calcular_dias_exceso(fecha_inicio, fecha_fin)
    if dias_exceso <= 0:
        return None

    return ArgumentoCandidato(
        regla_id="R009",
        descripcion=(
            "El procedimiento sancionador se ha tramitado durante mas "
            "de seis meses desde la notificacion de su inicio hasta la "
            "notificacion del acuerdo de imposicion de sancion. Este "
            "exceso sobre el plazo maximo legal determina la caducidad "
            "automatica del procedimiento, que ademas impide la "
            "iniciacion de un nuevo expediente sancionador sobre los "
            "mismos hechos."
        ),
        cita_normativa_propuesta=(
            "Caducidad del procedimiento sancionador por exceso del "
            "plazo maximo legal de tramitacion"
        ),
        datos_disparo={
            "documento_id": doc.id,
            "fecha_inicio_sancionador": fecha_inicio.date().isoformat(),
            "fecha_notificacion_sancion": fecha_fin.date().isoformat(),
            "plazo_maximo_meses": _PLAZO_MAX_MESES_SANCIONADOR,
            "dias_exceso": dias_exceso,
        },
        impacto_estimado=(
            "caducidad del procedimiento sancionador con imposibilidad "
            "de reiniciarlo"
        ),
    )
