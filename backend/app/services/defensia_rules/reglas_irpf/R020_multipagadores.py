"""R020 — multipagadores_obligacion_declarar (T1B-020).

Regla del Bloque II (IRPF). Modela el art. 96 LIRPF — obligacion de declarar
en su redaccion vigente tras la modificacion introducida por el Real
Decreto-ley de 2024 (RDL 4/2024). Para el ejercicio 2024 y siguientes:

    - Limite general: 22.000 EUR de rendimientos del trabajo anuales.
    - Limite de multipagadores: 15.876 EUR (antes 15.000 EUR) cuando el
      contribuyente ha percibido rendimientos de mas de un pagador y el
      segundo y restantes han abonado, en conjunto, mas de 1.500 EUR.

La regla dispara cuando la AEAT:

    - Aplica el limite general (22.000 EUR) a un contribuyente que debia
      haber estado sometido al limite de multipagadores (15.876 EUR), ya
      sea porque el importe del segundo pagador supera los 1.500 EUR o
      porque directamente se cita un "limite real procedente" distinto al
      aplicado.
    - Sanciona por no declarar a un contribuyente cuyos ingresos no llegan
      al umbral actualizado del 2024 (15.876 EUR), de modo que no existia
      obligacion material de presentar la declaracion.

La regla NO dispara cuando:

    - Los ingresos totales superan el limite general (22.000 EUR): el
      contribuyente estaba obligado a declarar con cualquiera de los dos
      limites y no hay conflicto que defender.
    - El segundo pagador no supera los 1.500 EUR: el limite de 22.000 EUR
      es el correcto por mandato del propio art. 96 LIRPF.

Invariante #2 (anti-alucinacion): la cita normativa devuelta por la regla
es SEMANTICA y libre. La cita canonica (articulo + ley + RDL) la resuelve
el ``defensia_rag_verifier`` contra el corpus normativo. Por eso aqui no
aparecen literales como "Art. 96 LIRPF" ni "RDL 4/2024" — solo terminos
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
# Constantes — limites y umbrales del art. 96 LIRPF tras RDL 4/2024
# ---------------------------------------------------------------------------

LIMITE_MULTIPAGADORES_2024 = 15876
"""Limite de rendimientos del trabajo para multipagadores en 2024+ (EUR).

Elevado desde 15.000 EUR por el Real Decreto-ley de 2024 en respuesta a la
subida del SMI. Aplica cuando el segundo y restantes pagadores abonan, en
conjunto, mas de 1.500 EUR.
"""

LIMITE_GENERAL = 22000
"""Limite general de rendimientos del trabajo anuales (EUR) — inalterado."""

UMBRAL_SEGUNDO_PAGADOR = 1500
"""Umbral que activa el limite de multipagadores (EUR).

Si la suma percibida del segundo y restantes pagadores supera los 1.500 EUR,
el limite aplicable pasa del general (22.000 EUR) al de multipagadores
(15.876 EUR en 2024+).
"""


# Cita semantica libre — el RAG verificador resuelve la cita canonica.
_CITA_SEMANTICA = (
    "Obligacion de declarar en supuestos de rendimientos del trabajo con "
    "mas de un pagador conforme al limite actualizado del Real Decreto-ley "
    "de 2024"
)


# Tipos de documento relevantes para la regla, en orden de preferencia. Se
# mira primero la liquidacion/propuesta (que es donde aparece el limite
# aplicado por la Administracion) y despues el acuerdo de imposicion de
# sancion (que es donde aparece la sancion por falta de presentacion).
_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)

_TIPOS_SANCION = (
    TipoDocumento.ACUERDO_IMPOSICION_SANCION,
)


# ---------------------------------------------------------------------------
# Regla
# ---------------------------------------------------------------------------

@regla(
    id="R020",
    tributos=[Tributo.IRPF.value],
    fases=[
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        Fase.SANCIONADOR_INICIADO.value,
        Fase.SANCIONADOR_PROPUESTA.value,
        Fase.SANCIONADOR_IMPUESTA.value,
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Obligacion de declarar con multiples pagadores mal aplicada por "
        "AEAT segun limite vigente en el ejercicio"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R020 sobre el expediente.

    Se recorren los documentos del expediente buscando tres disparadores,
    en orden de especificidad:

    1. Liquidacion/propuesta con ``ingresos_totales`` entre el limite real
       procedente y el limite general: AEAT aplico un limite mas alto del
       que debia. Excluye el caso en que ``ingresos_totales`` superan el
       limite general (no hay conflicto, estaba obligado en cualquier caso).
    2. Liquidacion/propuesta donde el ``segundo_pagador_importe`` supera
       el umbral de 1.500 EUR pero el ``limite_aplicado`` es el general:
       condicion del umbral multipagadores ignorada.
    3. Acuerdo de imposicion de sancion por no declarar con
       ``ingresos_declarante`` por debajo del umbral aplicable: la sancion
       carece de base material (no habia obligacion de declarar).

    Si ninguno dispara, devuelve ``None``. El filtrado por tributo/fase ya
    lo hace el motor antes de invocar esta funcion.
    """
    # -----------------------------------------------------------------------
    # Disparador 1 y 2 — liquidaciones / propuestas
    # -----------------------------------------------------------------------
    doc_liquidacion = next(
        (
            d
            for d in expediente.documentos
            if d.tipo_documento in _TIPOS_LIQUIDACION
        ),
        None,
    )
    if doc_liquidacion is not None:
        datos = doc_liquidacion.datos or {}

        # --- Disparador 1: comparacion limite_aplicado vs limite_real ---
        ingresos_totales = datos.get("ingresos_totales")
        limite_aplicado_aeat = datos.get("limite_aplicado_por_aeat")
        limite_real = datos.get("limite_real_procedente")
        multipagadores = bool(datos.get("multipagadores", False))

        if (
            multipagadores
            and isinstance(ingresos_totales, (int, float))
            and isinstance(limite_aplicado_aeat, (int, float))
            and isinstance(limite_real, (int, float))
            and limite_aplicado_aeat > limite_real
            and limite_real <= ingresos_totales <= limite_aplicado_aeat
        ):
            return ArgumentoCandidato(
                regla_id="R020",
                descripcion=(
                    "La Administracion ha aplicado el limite general de "
                    "obligacion de declarar cuando procedia el limite de "
                    "multipagadores actualizado por el Real Decreto-ley "
                    "de 2024, lo que determina que el contribuyente si "
                    "estaba obligado a presentar la declaracion."
                ),
                cita_normativa_propuesta=_CITA_SEMANTICA,
                datos_disparo={
                    "tipo": "limite_multipagadores_mal_aplicado",
                    "documento_id": doc_liquidacion.id,
                    "tipo_documento": doc_liquidacion.tipo_documento.value,
                    "ingresos_totales": ingresos_totales,
                    "limite_aplicado_por_aeat": limite_aplicado_aeat,
                    "limite_real_procedente": limite_real,
                    "ejercicio": datos.get("ejercicio"),
                },
                impacto_estimado="alto",
            )

        # --- Disparador 2: segundo pagador > umbral pero limite general ---
        segundo_pagador = datos.get("segundo_pagador_importe")
        limite_aplicado = datos.get("limite_aplicado")
        if (
            isinstance(segundo_pagador, (int, float))
            and isinstance(limite_aplicado, (int, float))
            and segundo_pagador > UMBRAL_SEGUNDO_PAGADOR
            and limite_aplicado == LIMITE_GENERAL
        ):
            return ArgumentoCandidato(
                regla_id="R020",
                descripcion=(
                    "El segundo pagador supera el umbral que activa el "
                    "limite de obligacion de declarar para multipagadores, "
                    "por lo que no procede aplicar el limite general y si "
                    "el limite actualizado del Real Decreto-ley de 2024."
                ),
                cita_normativa_propuesta=_CITA_SEMANTICA,
                datos_disparo={
                    "tipo": "limite_multipagadores_mal_aplicado",
                    "documento_id": doc_liquidacion.id,
                    "tipo_documento": doc_liquidacion.tipo_documento.value,
                    "segundo_pagador_importe": segundo_pagador,
                    "limite_aplicado": limite_aplicado,
                    "umbral_segundo_pagador": UMBRAL_SEGUNDO_PAGADOR,
                    "ejercicio": datos.get("ejercicio"),
                },
                impacto_estimado="alto",
            )

    # -----------------------------------------------------------------------
    # Disparador 3 — sancion por no declarar bajo el umbral real
    # -----------------------------------------------------------------------
    doc_sancion = next(
        (
            d
            for d in expediente.documentos
            if d.tipo_documento in _TIPOS_SANCION
        ),
        None,
    )
    if doc_sancion is not None:
        datos = doc_sancion.datos or {}
        ingresos_declarante = datos.get("ingresos_declarante")
        umbral = datos.get(
            "umbral_multipagadores_2024",
            LIMITE_MULTIPAGADORES_2024,
        )
        if (
            isinstance(ingresos_declarante, (int, float))
            and isinstance(umbral, (int, float))
            and ingresos_declarante < umbral
        ):
            return ArgumentoCandidato(
                regla_id="R020",
                descripcion=(
                    "La Administracion sanciona por falta de presentacion "
                    "de la declaracion pese a que los ingresos del "
                    "contribuyente no alcanzan el umbral actualizado por "
                    "el Real Decreto-ley de 2024, por lo que no existia "
                    "obligacion material de declarar."
                ),
                cita_normativa_propuesta=_CITA_SEMANTICA,
                datos_disparo={
                    "tipo": "sancion_sin_obligacion_declarar",
                    "documento_id": doc_sancion.id,
                    "tipo_documento": doc_sancion.tipo_documento.value,
                    "ingresos_declarante": ingresos_declarante,
                    "umbral_aplicable": umbral,
                    "ejercicio": datos.get("ejercicio"),
                },
                impacto_estimado="alto",
            )

    return None
