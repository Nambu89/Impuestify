"""R022 — iva_inversion_sujeto_pasivo (T1B-022).

Regla del Bloque III (Otros tributos — IVA). Modela el supuesto del art.
84.Uno.2.o LIVA — inversion del sujeto pasivo en operaciones interiores —
en sus cuatro ramas clasicas:

    - Ejecuciones de garantia inmobiliaria (dacion en pago, subasta):
      cuando se transmite un inmueble en ejecucion de una garantia, el
      adquirente se convierte en sujeto pasivo por ISP.
    - Renuncia a exenciones inmobiliarias del art. 20 LIVA: cuando el
      transmitente renuncia a la exencion en segundas y ulteriores entregas
      de edificaciones o en transmisiones de terrenos, la LIVA somete la
      operacion a ISP.
    - Entregas realizadas en el seno de un procedimiento concursal: el
      adquirente autorrepercute para proteger el credito tributario frente
      al concurso.
    - Ejecuciones de obra de urbanizacion de terrenos o rehabilitacion de
      edificaciones: cuando el contratista factura al promotor.

En todos estos casos, quien debe repercutir e ingresar el IVA NO es el
transmitente/prestador sino el adquirente/destinatario. La regla dispara
cuando la AEAT liquida IVA no repercutido al transmitente ignorando la
inversion del sujeto pasivo: la operacion estaba sujeta a ISP y el IVA
debia haberlo autorrepercutido el adquirente (con derecho simultaneo a
deduccion en la mayoria de los casos), por lo que la liquidacion al
transmitente carece de base material.

La regla NO dispara cuando:

    - El contribuyente ya aplico ISP correctamente (``isp_aplicado=True``).
    - Se trata de una operacion ordinaria (venta regular) no sujeta a ISP.

Invariante #2 (anti-alucinacion): la cita normativa devuelta por la regla
es SEMANTICA y libre. La cita canonica (art. + ley) la resuelve el
``defensia_rag_verifier`` contra el corpus normativo. Por eso aqui no
aparecen literales como "Art. 84 LIVA" ni "84.Uno.2.o" — solo terminos
semanticos descriptivos del supuesto.
"""
from __future__ import annotations

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import regla


# ---------------------------------------------------------------------------
# Constantes — tipos de operacion sujetos a ISP segun el art. 84.Uno.2.o LIVA
# ---------------------------------------------------------------------------

_TIPOS_OPERACION_ISP: frozenset[str] = frozenset(
    {
        "ejecucion_garantia_inmobiliaria",
        "renuncia_exencion_inmobiliaria",
        "entrega_concurso",
        "ejecucion_obra_urbanizacion",
        "ejecucion_obra_rehabilitacion",
    }
)
"""Conjunto de tipos de operacion en los que la LIVA somete la entrega/servicio
a inversion del sujeto pasivo. Si AEAT liquida IVA no repercutido en cualquiera
de estos escenarios, ignorando la ISP, la regla R022 dispara.
"""


# Cita semantica libre — el RAG verificador resuelve la cita canonica.
_CITA_SEMANTICA = (
    "Inversion del sujeto pasivo en el Impuesto sobre el Valor Anadido "
    "aplicable a operaciones concursales, renuncia a exenciones inmobiliarias, "
    "ejecuciones de garantia y obras de urbanizacion/rehabilitacion"
)


# Tipos de documento donde buscar el disparo — el conflicto sobre ISP aparece
# en liquidaciones y propuestas, no en facturas o escrituras (que son prueba
# documental subyacente, no acto administrativo).
_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


# ---------------------------------------------------------------------------
# Regla
# ---------------------------------------------------------------------------

@regla(
    id="R022",
    tributos=[Tributo.IVA.value],
    fases=[
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Inversion del sujeto pasivo en IVA no aplicada cuando procede "
        "legalmente"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R022 sobre el expediente.

    Recorre los documentos de liquidacion/propuesta buscando operaciones
    cuyo ``tipo_operacion`` este en ``_TIPOS_OPERACION_ISP`` y en las que
    el contribuyente NO haya aplicado ISP (``isp_aplicado`` ausente o
    falsa). Si ademas el transmitente repercutio IVA (marca clasica de
    "pensaba que era operacion ordinaria"), la liquidacion al transmitente
    carece de base material.

    Devuelve un unico ``ArgumentoCandidato`` en el primer documento que
    dispare. Si ningun documento cumple, devuelve ``None``. El filtrado por
    tributo/fase ya lo hace el motor antes de invocar esta funcion.
    """
    for doc in expediente.documentos:
        if doc.tipo_documento not in _TIPOS_LIQUIDACION:
            continue

        datos = doc.datos or {}

        tipo_operacion = datos.get("tipo_operacion")
        if tipo_operacion not in _TIPOS_OPERACION_ISP:
            continue

        # Si el contribuyente ya aplico ISP correctamente, no hay nada que
        # defender — la regla debe permanecer silente.
        if bool(datos.get("isp_aplicado", False)):
            continue

        # Senal dura: el transmitente repercutio IVA (tipico en operaciones
        # donde el contribuyente no se dio cuenta de que procedia ISP) o
        # bien AEAT liquida IVA no repercutido. Cualquiera de las dos
        # senales basta para disparar.
        iva_repercutido = bool(
            datos.get("iva_repercutido_por_transmitente", False)
        )
        aeat_liquida = bool(
            datos.get("aeat_liquida_iva_no_repercutido", False)
        )
        if not (iva_repercutido or aeat_liquida):
            continue

        return ArgumentoCandidato(
            regla_id="R022",
            descripcion=(
                "La Administracion liquida IVA al transmitente en una "
                "operacion sometida a inversion del sujeto pasivo, cuando "
                "el obligado a autorrepercutir e ingresar el impuesto es "
                "el adquirente. La inversion del sujeto pasivo opera por "
                "ministerio de la ley en ejecuciones de garantia "
                "inmobiliaria, renuncias a exenciones inmobiliarias, "
                "entregas realizadas en concurso y obras de "
                "urbanizacion/rehabilitacion, por lo que la liquidacion "
                "al transmitente carece de base material."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "tipo": "iva_isp_no_aplicada",
                "documento_id": doc.id,
                "tipo_documento": doc.tipo_documento.value,
                "tipo_operacion": tipo_operacion,
                "iva_repercutido_por_transmitente": iva_repercutido,
                "aeat_liquida_iva_no_repercutido": aeat_liquida,
                "ejercicio": datos.get("ejercicio"),
            },
            impacto_estimado="alto",
        )

    return None
