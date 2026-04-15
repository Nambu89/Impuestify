"""R003 — prescripcion_4_anos (T1B-003).

Regla transversal que dispara cuando la AEAT notifica el inicio de actuaciones
sobre un ejercicio cuyo derecho a liquidar ya ha prescrito por el transcurso
de mas de 4 anos desde el fin del plazo voluntario de declaracion.

Base normativa:
- Art. 66.a) Ley 58/2003 General Tributaria — prescripcion del derecho a
  determinar la deuda tributaria mediante la oportuna liquidacion a los 4 anos.
- Art. 67.1 LGT — computo desde el dia siguiente a aquel en que finalice el
  plazo reglamentario para presentar la declaracion o autoliquidacion.
- Art. 68 LGT — causas de interrupcion (cualquier accion de la Administracion
  con conocimiento formal del obligado tributario).

Doctrina TS: el plazo de 4 anos se computa "de fecha a fecha" (STS Sala 3.ª).
Por tanto, un acto notificado el 2025-07-01 cuando el fin del plazo voluntario
fue el 2021-06-30 SI supera el plazo (4 anos + 1 dia).

Absorbe el sub-caso "calculo de plazos" (antigua R008 del plan v1, descartada
como regla autonoma segun decision del research doc).
"""
from __future__ import annotations

from datetime import date, datetime, timezone  # noqa: F401 — datetime exportado para patch en tests
from typing import Optional

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    DocumentoEstructurado,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import regla


# ---------------------------------------------------------------------------
# Constantes auxiliares
# ---------------------------------------------------------------------------

# Documentos emitidos por la AEAT (vs. ESCRITO_*_USUARIO o auxiliares). Son los
# unicos que pueden interrumpir o iniciar el computo de prescripcion.
_TIPOS_ACTO_AEAT: frozenset[TipoDocumento] = frozenset({
    TipoDocumento.REQUERIMIENTO,
    TipoDocumento.PROPUESTA_LIQUIDACION,
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.ACUERDO_INICIO_SANCIONADOR,
    TipoDocumento.PROPUESTA_SANCION,
    TipoDocumento.ACUERDO_IMPOSICION_SANCION,
    TipoDocumento.ACTA_INSPECCION,
    TipoDocumento.PROVIDENCIA_APREMIO,
    TipoDocumento.RESOLUCION_TEAR,
    TipoDocumento.RESOLUCION_TEAC,
})

# Fases donde la prescripcion puede ser un argumento util. Usamos los valores
# literales del enum `Fase` tal como esta definido hoy en models.defensia.
_FASES_APLICABLES: list[str] = [
    Fase.COMPROBACION_REQUERIMIENTO.value,
    Fase.COMPROBACION_PROPUESTA.value,
    Fase.COMPROBACION_POST_ALEGACIONES.value,
    Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
    Fase.SANCIONADOR_INICIADO.value,
    Fase.SANCIONADOR_PROPUESTA.value,
    Fase.SANCIONADOR_IMPUESTA.value,
    Fase.REPOSICION_INTERPUESTA.value,
    Fase.TEAR_INTERPUESTA.value,
    Fase.TEAR_AMPLIACION_POSIBLE.value,
]

_CITA_PROPUESTA = (
    "Posible prescripcion del derecho de la Administracion a liquidar (arts. "
    "66.a y 67.1 de la Ley 58/2003 General Tributaria), con computo de fecha "
    "a fecha del plazo de 4 anos conforme a la doctrina del Tribunal Supremo."
)


# ---------------------------------------------------------------------------
# Helpers deterministas (Python puro, sin LLM)
# ---------------------------------------------------------------------------

def _fin_plazo_voluntario(ejercicio: int, tributo: Tributo) -> date:
    """Devuelve el ultimo dia del plazo voluntario de declaracion del ejercicio.

    Simplificacion pragmatica:
    - IRPF: 30 de junio del ano siguiente al ejercicio (fin campana renta).
    - Otros tributos (IVA, ISD, ITP, Plusvalia): se asume tambien 30 de junio
      del ano siguiente como cota conservadora en favor del contribuyente
      (dispara antes, permite al RAG verificador / writer afinar). Los plazos
      exactos de cada modelo se refinaran en R023-R030 cuando sea relevante.
    """
    # Tributo no afecta al fin de plazo en esta version pragmatica; se mantiene
    # en la firma por claridad y para facilitar evolucion futura.
    del tributo  # evita unused-argument
    return date(ejercicio + 1, 6, 30)


def _ejercicio_del_expediente(
    expediente: ExpedienteEstructurado,
) -> Optional[int]:
    """Busca el ejercicio fiscal en los `datos` de los documentos.

    Usa el primer documento AEAT con `datos.ejercicio` no nulo (en orden
    cronologico). Si no encuentra ninguno, intenta cualquier documento.
    """
    timeline = expediente.timeline_ordenado()

    # Primero buscamos en actos AEAT (mas fiables).
    for doc in timeline:
        if doc.tipo_documento in _TIPOS_ACTO_AEAT:
            ejercicio = doc.datos.get("ejercicio")
            if isinstance(ejercicio, int):
                return ejercicio

    # Fallback: cualquier documento con ejercicio.
    for doc in timeline:
        ejercicio = doc.datos.get("ejercicio")
        if isinstance(ejercicio, int):
            return ejercicio

    return None


def _primer_acto_aeat(
    expediente: ExpedienteEstructurado,
) -> Optional[DocumentoEstructurado]:
    """Devuelve el primer acto AEAT con `fecha_acto` no nula, en orden ASC.

    Este es el punto de referencia para medir el plazo: la AEAT interrumpe
    la prescripcion con la primera accion notificada al obligado tributario
    (art. 68 LGT). Si el PRIMER acto AEAT ya esta fuera de plazo, no ha
    podido haber interrupcion anterior valida y la regla dispara.
    """
    for doc in expediente.timeline_ordenado():
        if doc.tipo_documento in _TIPOS_ACTO_AEAT and doc.fecha_acto is not None:
            return doc
    return None


def _hay_interrupcion_explicita(expediente: ExpedienteEstructurado) -> bool:
    """Heuristica: algun documento trae `datos.hubo_interrupcion=True`.

    Flag usado por extractores avanzados (o fixtures de test) para indicar
    que se detecto una accion interruptiva previa incluso si no esta
    modelada como documento en el expediente (por ejemplo un requerimiento
    antiguo no digitalizado pero referenciado en una liquidacion posterior).
    """
    for doc in expediente.documentos:
        if doc.datos.get("hubo_interrupcion") is True:
            return True
    return False


# ---------------------------------------------------------------------------
# Regla
# ---------------------------------------------------------------------------

@regla(
    id="R003",
    tributos=[
        Tributo.IRPF.value,
        Tributo.IVA.value,
        Tributo.ISD.value,
        Tributo.ITP.value,
        Tributo.PLUSVALIA.value,
    ],
    fases=_FASES_APLICABLES,
    descripcion=(
        "Posible prescripcion del derecho a liquidar: el primer acto AEAT se "
        "notifica cuando ya han transcurrido mas de 4 anos desde el fin del "
        "plazo voluntario de declaracion (arts. 66.a y 67 LGT, computo fecha "
        "a fecha)."
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,
) -> Optional[ArgumentoCandidato]:
    """Evalua R003 sobre el expediente.

    Devuelve un `ArgumentoCandidato` si dispara, o `None` si no procede. La
    cita normativa es SEMANTICA (la cita exacta verbatim la construye el
    writer service + RAG verificador en Parte 2).
    """
    del brief  # la regla no necesita el texto del usuario para disparar

    ejercicio = _ejercicio_del_expediente(expediente)
    if ejercicio is None:
        return None

    primer_acto = _primer_acto_aeat(expediente)
    if primer_acto is None or primer_acto.fecha_acto is None:
        return None

    if _hay_interrupcion_explicita(expediente):
        return None

    fin_plazo = _fin_plazo_voluntario(ejercicio, expediente.tributo)

    # Computo "de fecha a fecha": el plazo vence el mismo dia y mes, 4 anos
    # despues. Un acto notificado el dia siguiente ya esta fuera de plazo.
    # Ej: fin_plazo = 2021-06-30 -> limite = 2025-06-30, prescripcion a partir
    # de 2025-07-01 inclusive.
    limite_prescripcion = date(fin_plazo.year + 4, fin_plazo.month, fin_plazo.day)

    fecha_notif = primer_acto.fecha_acto.date()

    if fecha_notif <= limite_prescripcion:
        return None

    dias_transcurridos = (fecha_notif - fin_plazo).days

    return ArgumentoCandidato(
        regla_id="R003",
        descripcion=(
            "El primer acto de la AEAT frente al obligado tributario se "
            "notifica cuando ya han transcurrido mas de 4 anos desde el fin "
            "del plazo voluntario de declaracion, lo que determina la "
            "prescripcion del derecho a liquidar conforme a los articulos "
            "66.a y 67 LGT en su computo de fecha a fecha."
        ),
        cita_normativa_propuesta=_CITA_PROPUESTA,
        datos_disparo={
            "ejercicio": ejercicio,
            "fin_plazo_voluntario": fin_plazo.isoformat(),
            "limite_prescripcion": limite_prescripcion.isoformat(),
            "fecha_primer_acto_aeat": fecha_notif.isoformat(),
            "tipo_primer_acto": primer_acto.tipo_documento.value,
            "dias_transcurridos": dias_transcurridos,
        },
        impacto_estimado="ALTO",
    )
