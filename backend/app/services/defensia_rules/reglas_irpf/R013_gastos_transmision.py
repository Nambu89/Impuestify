"""R013 — gastos_inherentes_transmision_inmueble (T1B-013).

Regla determinista DefensIA para IRPF. Dispara cuando, al regularizar una
ganancia patrimonial por transmision de inmueble, AEAT no computa los gastos
y tributos inherentes a la adquisicion y/o a la transmision que el
contribuyente habia declarado.

Tres patrones de disparo:

1. **Gastos de adquisicion omitidos** — AEAT elimina del valor de adquisicion
   los gastos accesorios declarados (notaria, registro, gestoria, ITP/IVA
   soportado, tasacion, comision inmobiliaria de la compra en su dia). Esto
   incrementa artificialmente la ganancia patrimonial.

2. **Comision inmobiliaria de la transmision no admitida** — el vendedor
   satisfizo comision a una agencia inmobiliaria para vender el inmueble y
   AEAT no la minora del valor de transmision. Criterio DGT V2625-20: la
   comision es un gasto inherente a la transmision.

3. **Plusvalia municipal satisfecha no computada** — el IIVTNU pagado por el
   transmitente es un tributo inherente a la transmision y debe minorar el
   valor de transmision en el calculo de la ganancia patrimonial.

Relevancia en el caso David Oliva (ground truth del producto): si AEAT deniega
la exencion por reinversion en vivienda habitual, la ganancia tributa y es
imprescindible asegurarse de que todos los gastos inherentes esten computados
para minimizar la base imponible regularizada. Condicional pero probable.

Base normativa (la RESUELVE el RAG verificador, NO la regla — invariante #2):
    - Art. 35.1.b) LIRPF — valor de adquisicion incluye gastos y tributos
      inherentes a la adquisicion satisfechos por el adquirente.
    - Art. 35.2 LIRPF — valor de transmision se minora en gastos y tributos
      inherentes a la transmision satisfechos por el transmitente.
    - DGT V2625-20 — comision inmobiliaria como gasto computable.

Invariante #2 (anti-alucinacion): la regla emite una cita SEMANTICA. El texto
canonico lo traduce el RAG verificador contra el corpus normativo. Zero
hardcoded article references en este modulo.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T1B-013
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


# ---------------------------------------------------------------------------
# Citas semanticas — describen el concepto juridico, nunca el articulo
# ---------------------------------------------------------------------------

_CITA_SEMANTICA = (
    "Gastos y tributos inherentes a la adquisicion y transmision de inmuebles "
    "no computados en el calculo de la ganancia patrimonial: el valor de "
    "adquisicion debe incluir los gastos accesorios satisfechos por el "
    "adquirente y el valor de transmision debe minorarse en los gastos y "
    "tributos inherentes soportados por el transmitente"
)


# ---------------------------------------------------------------------------
# Detectores individuales — cada uno analiza un sub-patron
# ---------------------------------------------------------------------------

def _detectar_gastos_adquisicion_omitidos(datos: dict) -> Optional[dict]:
    """Patron 1: gastos de adquisicion declarados pero no computados.

    Devuelve `datos_disparo` si el patron aplica, None en caso contrario.
    Defaults conservadores: si los campos no existen, no disparamos.
    """
    incluidos = datos.get("gastos_adquisicion_incluidos")
    declarados = datos.get("gastos_adquisicion_declarados")

    if incluidos is False and declarados is not None and declarados > 0:
        return {
            "tipo": "adquisicion",
            "gastos_omitidos": declarados,
        }
    return None


def _detectar_comision_inmobiliaria_no_admitida(datos: dict) -> Optional[dict]:
    """Patron 2: comision inmobiliaria de la transmision declarada pero
    admitida solo parcialmente (o nada) por AEAT.

    Dispara cuando el importe admitido es estrictamente menor que el
    declarado. El delta es el importe omitido.
    """
    declarada = datos.get("comision_inmobiliaria_declarada")
    admitida = datos.get("comision_inmobiliaria_admitida")

    if declarada is None or admitida is None:
        return None
    if declarada <= 0:
        return None
    if admitida >= declarada:
        return None

    return {
        "tipo": "transmision_comision_inmobiliaria",
        "gastos_omitidos": declarada - admitida,
    }


def _detectar_plusvalia_municipal_no_computada(datos: dict) -> Optional[dict]:
    """Patron 3: plusvalia municipal satisfecha pero no incluida en el
    calculo del valor de transmision.
    """
    satisfecha = datos.get("plusvalia_municipal_satisfecha")
    incluida = datos.get("plusvalia_incluida_en_calculo")

    if satisfecha is None or satisfecha <= 0:
        return None
    if incluida is not False:
        # Solo disparamos cuando se ha dicho explicitamente que NO esta
        # incluida. Si el campo falta asumimos benefit of the doubt.
        return None

    return {
        "tipo": "transmision_plusvalia_municipal",
        "gastos_omitidos": satisfecha,
    }


# ---------------------------------------------------------------------------
# Registro de la regla
# ---------------------------------------------------------------------------

@regla(
    id="R013",
    tributos=[Tributo.IRPF.value],
    fases=[
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Ganancia patrimonial sin computar los gastos y tributos inherentes "
        "a la adquisicion o transmision del inmueble"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — brief no usado por R013
) -> Optional[ArgumentoCandidato]:
    """Evalua R013 sobre el expediente.

    Recorre los documentos en busca del primer acto (liquidacion provisional
    o propuesta de liquidacion) en el que se regularice una ganancia
    patrimonial por transmision de inmueble con alguno de los tres patrones
    de gastos omitidos.

    Returns:
        ArgumentoCandidato | None: candidato si dispara, None si no.
    """
    del brief

    tipos_objetivo = (
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        TipoDocumento.PROPUESTA_LIQUIDACION,
    )

    for doc in expediente.documentos:
        if doc.tipo_documento not in tipos_objetivo:
            continue

        datos = doc.datos or {}
        if datos.get("ganancia_patrimonial_inmueble") is not True:
            continue

        for detector in (
            _detectar_gastos_adquisicion_omitidos,
            _detectar_comision_inmobiliaria_no_admitida,
            _detectar_plusvalia_municipal_no_computada,
        ):
            disparo = detector(datos)
            if disparo is None:
                continue

            disparo["documento_id"] = doc.id
            disparo["tipo_documento"] = doc.tipo_documento.value

            return ArgumentoCandidato(
                regla_id="R013",
                descripcion=(
                    "La regularizacion practicada por la Administracion no "
                    "computa los gastos y tributos inherentes a la "
                    "adquisicion o transmision del inmueble declarados y "
                    "acreditables por el contribuyente, lo que incrementa "
                    "indebidamente la ganancia patrimonial imputada."
                ),
                cita_normativa_propuesta=_CITA_SEMANTICA,
                datos_disparo=disparo,
                impacto_estimado=(
                    "Reduccion de la ganancia patrimonial regularizada por "
                    "el importe de los gastos y tributos inherentes omitidos, "
                    "con la consiguiente minoracion de la cuota y, en su "
                    "caso, de los intereses y recargos asociados."
                ),
            )

    return None
