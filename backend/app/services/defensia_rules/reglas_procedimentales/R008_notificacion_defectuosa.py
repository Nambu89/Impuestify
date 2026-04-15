"""R008 — notificacion_defectuosa (T1B-008).

Detecta notificaciones administrativas con defectos formales esenciales que
provocan anulabilidad del acto hasta su correcta practica. Tres patrones de
disparo, todos ellos transversales a los cinco tributos de DefensIA v1:

1. **DEHu sin puesta a disposicion efectiva**: canal Direccion Electronica
   Habilitada unica sin que conste puesta a disposicion efectiva del acto
   en el buzon del obligado tributario.
2. **Postal sin segundo intento**: notificacion por correo con un solo
   intento fallido y sin acuse, incumpliendo el doble intento exigido por
   la normativa tributaria.
3. **Domicilio incorrecto**: notificacion practicada en un domicilio que no
   coincide con el que el obligado tiene declarado en el Censo.

Base normativa (la RESUELVE el RAG verificador, NO la regla):
- Arts. 109-112 LGT (notificaciones tributarias)
- Art. 41 Ley 39/2015 (regimen general de notificaciones administrativas)
- Real Decreto 203/2021 (DEHu y notificaciones electronicas)
- STC 112/2019 sobre notificaciones electronicas y derecho al recurso efectivo

Invariante #2 (anti-alucinacion): la regla NO hardcodea cita canonica. Emite
una cita SEMANTICA que describe el defecto formal en lenguaje juridico
generico ("notificacion defectuosa por incumplimiento de requisitos formales
esenciales"). El verificador RAG la traduce al texto normativo exacto contra
el corpus indexado.
"""
from __future__ import annotations

from typing import Any, Optional

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
# El RAG verificador la traducira a "Arts. 109-112 LGT + art. 41 Ley 39/2015
# + RD 203/2021 + STC 112/2019" contra el corpus normativo.
_CITA_SEMANTICA = (
    "Notificacion defectuosa por incumplimiento de requisitos formales "
    "esenciales en la puesta a disposicion del acto administrativo, con "
    "vicio de anulabilidad que demora la eficacia hasta su correcta practica"
)


# Tipos de documentos "acto administrativo" cuya notificacion puede ser
# impugnable. Ignoramos escritos del propio contribuyente (alegaciones, etc.)
# porque la notificacion del obligado a si mismo no tiene sentido.
_TIPOS_ACTO_NOTIFICABLE: frozenset[TipoDocumento] = frozenset(
    {
        TipoDocumento.REQUERIMIENTO,
        TipoDocumento.PROPUESTA_LIQUIDACION,
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        TipoDocumento.ACUERDO_INICIO_SANCIONADOR,
        TipoDocumento.PROPUESTA_SANCION,
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        TipoDocumento.RESOLUCION_TEAR,
        TipoDocumento.RESOLUCION_TEAC,
    }
)


def _detecta_defecto(datos: dict[str, Any]) -> Optional[str]:
    """Inspecciona los `datos` de un documento y devuelve el codigo del
    defecto de notificacion detectado, o None si la notificacion es correcta.

    Orden de prioridad:
        1. Domicilio que no coincide con el registro (defecto mas grave).
        2. DEHu sin puesta a disposicion efectiva.
        3. Postal sin segundo intento.
    """
    # 1. Domicilio incorrecto — no depende del canal.
    if datos.get("domicilio_coincide_con_registro") is False:
        return "domicilio_no_coincide_con_registro"

    canal = str(datos.get("canal_notificacion", "")).upper()

    # 2. DEHu sin puesta a disposicion efectiva.
    if canal == "DEHU" and datos.get("puesta_disposicion_efectiva") is False:
        return "dehu_sin_puesta_disposicion_efectiva"

    # 3. Postal sin segundo intento.
    if canal == "POSTAL":
        intentos = datos.get("numero_intentos")
        acuse = datos.get("acuse_recibido")
        if (
            isinstance(intentos, int)
            and intentos < 2
            and acuse is False
        ):
            return "postal_sin_segundo_intento"

    return None


def _descripcion_por_motivo(motivo: str) -> str:
    """Descripcion textual del argumento segun el motivo concreto detectado."""
    if motivo == "dehu_sin_puesta_disposicion_efectiva":
        return (
            "La notificacion se practico por Direccion Electronica Habilitada "
            "unica sin que conste puesta a disposicion efectiva del acto en "
            "el buzon del obligado tributario."
        )
    if motivo == "postal_sin_segundo_intento":
        return (
            "La notificacion postal se dio por practicada con un unico "
            "intento fallido y sin acuse de recibo, incumpliendo la exigencia "
            "del doble intento antes de acudir a otras formas subsidiarias."
        )
    if motivo == "domicilio_no_coincide_con_registro":
        return (
            "La notificacion se dirigio a un domicilio que no coincide con "
            "el declarado por el obligado tributario en el Censo, privandole "
            "del conocimiento del acto y del ejercicio efectivo de su derecho "
            "de defensa."
        )
    return "Notificacion con defecto formal esencial."


@regla(
    id="R008",
    tributos=[
        Tributo.IRPF.value,
        Tributo.IVA.value,
        Tributo.ISD.value,
        Tributo.ITP.value,
        Tributo.PLUSVALIA.value,
    ],
    fases=[
        # Liquidacion provisional firme con plazo de recurso abierto.
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        # Procedimiento sancionador (cualquier momento).
        Fase.SANCIONADOR_INICIADO.value,
        Fase.SANCIONADOR_PROPUESTA.value,
        Fase.SANCIONADOR_IMPUESTA.value,
        # Propuesta de liquidacion en comprobacion limitada.
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        # Requerimiento previo — alegable de entrada.
        Fase.COMPROBACION_REQUERIMIENTO.value,
        # Reposicion y TEAR — sigue siendo argumentable.
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Notificacion defectuosa del acto administrativo con defecto formal "
        "esencial (DEHu sin puesta a disposicion, postal sin segundo intento "
        "o domicilio que no coincide con el declarado en el Censo)"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — brief no usado, la regla es puramente documental
) -> Optional[ArgumentoCandidato]:
    """Evalua R008 sobre el expediente.

    Recorre el timeline buscando actos administrativos notificables con
    defecto formal en sus datos de notificacion. Dispara al primer defecto
    detectado (la regla es disyuntiva, basta con un defecto acreditado para
    plantear la anulabilidad).
    """
    for doc in expediente.timeline_ordenado():
        if doc.tipo_documento not in _TIPOS_ACTO_NOTIFICABLE:
            continue

        datos = doc.datos or {}
        motivo = _detecta_defecto(datos)
        if motivo is None:
            continue

        datos_disparo: dict[str, Any] = {
            "motivo": motivo,
            "documento_id": doc.id,
            "tipo_documento": doc.tipo_documento.value,
            "canal_notificacion": datos.get("canal_notificacion"),
        }
        # Anadimos solo los campos relevantes al motivo concreto para dar
        # contexto al escrito posterior sin inflar el payload.
        if motivo == "dehu_sin_puesta_disposicion_efectiva":
            datos_disparo["puesta_disposicion_efectiva"] = (
                datos.get("puesta_disposicion_efectiva")
            )
        elif motivo == "postal_sin_segundo_intento":
            datos_disparo["numero_intentos"] = datos.get("numero_intentos")
            datos_disparo["acuse_recibido"] = datos.get("acuse_recibido")
        elif motivo == "domicilio_no_coincide_con_registro":
            datos_disparo["domicilio_coincide_con_registro"] = (
                datos.get("domicilio_coincide_con_registro")
            )

        return ArgumentoCandidato(
            regla_id="R008",
            descripcion=_descripcion_por_motivo(motivo),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo=datos_disparo,
            impacto_estimado=(
                "Alegable en reposicion o TEAR: anulabilidad del acto por "
                "notificacion defectuosa; la eficacia del acto queda "
                "demorada hasta que se practique correctamente, con posible "
                "reapertura del plazo de recurso."
            ),
        )

    return None
