"""R004 — carga_prueba_administracion (T1B-004).

Detecta los supuestos en que la Administracion tributaria (AEAT) deniega una
deduccion, exencion u otro beneficio fiscal SIN haber ejercido la carga
probatoria que le corresponde.

Dos patrones de disparo:

1. **Sin requerimiento previo**: AEAT deniega directamente un beneficio fiscal
   sin haber requerido antes documentacion al contribuyente. La Administracion
   esta obligada, cuando el contribuyente aporta principio de prueba (o cuando
   los hechos son de facil disponibilidad para ella), a desplegar una
   actividad probatoria minima antes de denegar.

2. **Aportada sin motivar la insuficiencia**: el contribuyente SI aporto
   documentacion en respuesta a un requerimiento, pero AEAT deniega sin
   motivar por que esa documentacion resulta insuficiente para acreditar el
   hecho imponible. Esto vulnera igualmente la carga probatoria administrativa.

Base normativa (la RESUELVE el RAG verificador, NO la regla):
- Art. 105.1 LGT
- Doctrina TS sobre facilidad y disponibilidad probatoria
- Art. 217 LEC supletoriamente

Invariante #2 (anti-alucinacion): la regla NO hardcodea cita canonica. Emite
una cita SEMANTICA que describe el concepto juridico ("Incumplimiento de la
carga de la prueba por la Administracion"). El RAG verificador la traduce al
texto canonico exacto contra el corpus indexado.
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


# Cita semantica — describe el concepto juridico, nunca el articulo.
# El RAG verificador la traducira a "Art. 105.1 LGT + doctrina TS de facilidad
# y disponibilidad probatoria" contra el corpus normativo.
_CITA_SEMANTICA = (
    "Incumplimiento de la carga de la prueba por la Administracion: doctrina "
    "de facilidad y disponibilidad probatoria aplicable cuando el obligado "
    "tributario aporta principio de prueba o cuando los hechos son de natural "
    "disponibilidad para la propia Administracion"
)


def _es_liquidacion_que_deniega_beneficio(
    expediente: ExpedienteEstructurado,
) -> Optional[dict]:
    """Busca en el timeline una liquidacion provisional que deniegue un
    beneficio fiscal (deduccion, exencion, reduccion, bonificacion).

    Devuelve el dict de `datos` del documento disparador, o None si no hay
    ninguna liquidacion que cumpla el criterio.
    """
    for doc in expediente.timeline_ordenado():
        if doc.tipo_documento != TipoDocumento.LIQUIDACION_PROVISIONAL:
            continue
        datos = doc.datos or {}
        if datos.get("deniega_beneficio_fiscal") is True:
            return datos
    return None


def _hay_requerimiento_previo(expediente: ExpedienteEstructurado) -> bool:
    """True si existe al menos un documento de tipo REQUERIMIENTO en el
    expediente.

    No se comprueba el orden temporal estrictamente porque en la practica el
    requerimiento siempre precede a la liquidacion provisional; cuando no hay
    fechas fiables usamos la mera existencia del documento como proxy.
    """
    return any(
        doc.tipo_documento == TipoDocumento.REQUERIMIENTO
        for doc in expediente.documentos
    )


@regla(
    id="R004",
    tributos=[
        Tributo.IRPF.value,
        Tributo.IVA.value,
        Tributo.ISD.value,
        Tributo.ITP.value,
        Tributo.PLUSVALIA.value,
    ],
    fases=[
        # Liquidacion provisional firme aun con plazo de recurso.
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        # Procedimiento sancionador (cualquier momento).
        Fase.SANCIONADOR_INICIADO.value,
        Fase.SANCIONADOR_PROPUESTA.value,
        Fase.SANCIONADOR_IMPUESTA.value,
        # Propuesta de liquidacion en comprobacion limitada.
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        # Reposicion y TEAR — sigue siendo argumentable.
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "AEAT deniega un beneficio fiscal sin ejercer la carga de la prueba "
        "que le incumbe (doctrina de facilidad y disponibilidad probatoria)"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado, brief: Brief  # noqa: ARG001 — brief no usado
) -> Optional[ArgumentoCandidato]:
    """Evalua R004 sobre el expediente.

    Dispara cuando:
    - Hay liquidacion provisional denegando un beneficio fiscal, Y
    - No hubo requerimiento previo de documentacion, O
    - Si lo hubo y el contribuyente aporto, AEAT no motivo por que la
      documentacion resulta insuficiente.
    """
    datos_liq = _es_liquidacion_que_deniega_beneficio(expediente)
    if datos_liq is None:
        # No hay denegacion de beneficio fiscal — la regla no aplica.
        # Esto cubre tambien el negativo de la mera correccion aritmetica.
        return None

    hay_requerimiento = _hay_requerimiento_previo(expediente)

    if not hay_requerimiento:
        # Patron 1: denegacion directa sin siquiera pedir pruebas.
        return ArgumentoCandidato(
            regla_id="R004",
            descripcion=(
                "La Administracion denego el beneficio fiscal sin requerir "
                "previamente documentacion al obligado tributario, "
                "incumpliendo la carga probatoria que le incumbe."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "motivo": "sin_requerimiento_previo",
                "concepto_denegado": datos_liq.get("concepto_denegado"),
                "documentacion_aportada": False,
                "hay_requerimiento_previo": False,
            },
            impacto_estimado=(
                "Alegable en reposicion o TEAR: inversion de la carga de la "
                "prueba y retroaccion de actuaciones para permitir aportacion."
            ),
        )

    # Patron 2: hubo requerimiento. Miramos si la denegacion esta motivada.
    documentacion_aportada = datos_liq.get("documentacion_aportada") is True
    motivacion_suficiente = datos_liq.get("motivacion_insuficiencia_prueba") is True

    if documentacion_aportada and not motivacion_suficiente:
        return ArgumentoCandidato(
            regla_id="R004",
            descripcion=(
                "El obligado tributario aporto la documentacion requerida, "
                "pero la Administracion denego el beneficio sin motivar por "
                "que dicha documentacion resulta insuficiente para acreditar "
                "los hechos constitutivos del derecho."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "motivo": "aportada_sin_motivar_insuficiencia",
                "concepto_denegado": datos_liq.get("concepto_denegado"),
                "documentacion_aportada": True,
                "hay_requerimiento_previo": True,
            },
            impacto_estimado=(
                "Alegable en reposicion o TEAR: falta de motivacion "
                "probatoria. Posible nulidad del acto por indefension."
            ),
        )

    # Requerimiento + respuesta + denegacion motivada: la Administracion SI
    # cumplio su carga probatoria. R004 calla.
    return None
