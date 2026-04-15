"""R025 — itp_valor_referencia (T2-R025).

Regla determinista DefensIA para ITP. Dispara cuando la liquidacion aplica
como base imponible el valor de referencia catastral fijado por la Direccion
General del Catastro y el contribuyente dispone de una prueba pericial
(tasacion pericial contradictoria o informe tecnico cualificado) que acredita
un valor real inferior al de referencia utilizado por la Administracion.

Contexto normativo (la RESUELVE el RAG verificador, NO la regla — invariante #2):
    - Art. 10.2 TRLITPAJD (redaccion dada por la Ley 11/2021) — regla general:
      base imponible = mayor de (valor declarado, valor de referencia). Si el
      valor declarado es menor, prevalece el de referencia.
    - TC 2024 — desestima la inconstitucionalidad general del nuevo sistema
      de valor de referencia pero admite expresamente la impugnacion
      individualizada mediante prueba pericial en contrario. Esta via
      individualizada es la que R025 habilita a detectar.

Patrones de disparo:

1. **Tasacion pericial contradictoria** — el contribuyente ha encargado una
   tasacion pericial contradictoria (en sentido propio del art. 57.2 LGT o
   bien una tasacion aportada de parte) que concluye un valor real inferior
   al valor de referencia aplicado en la liquidacion.

2. **Informe tecnico discrepante** — alternativamente, un informe tecnico
   emitido por tasador homologado o arquitecto con valoracion razonada que
   tambien discrepa del valor de referencia a la baja.

Salvaguardas negativas:

- **Sin prueba pericial** la regla no dispara: el TC exige soporte probatorio
  cualificado para la impugnacion individualizada, por lo que sin tasacion ni
  informe no hay defensa util.
- **Valor declarado >= valor de referencia**: la base imponible ya es la
  declarada (la ley toma el mayor), no hay regularizacion al alza que
  impugnar.
- **Tributo != ITP**: fuera de scope.

Invariante #2 (anti-alucinacion): la regla emite una cita SEMANTICA. El texto
canonico lo traduce el RAG verificador contra el corpus normativo. Zero
hardcoded article references en este modulo.

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T2-R025
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
    "Impugnacion individualizada de la base imponible determinada por valor "
    "de referencia catastral en transmisiones patrimoniales onerosas cuando "
    "se acredita valor inferior mediante tasacion pericial contradictoria o "
    "informe tecnico cualificado"
)


# ---------------------------------------------------------------------------
# Detectores individuales — cada uno analiza un sub-patron
# ---------------------------------------------------------------------------

def _extraer_valor_referencia(datos: dict) -> Optional[float]:
    """Devuelve el valor de referencia catastral declarado como base imponible
    en el documento, si existe y es estrictamente positivo."""
    valor = datos.get("base_imponible_valor_referencia")
    if valor is None:
        return None
    try:
        valor_f = float(valor)
    except (TypeError, ValueError):
        return None
    if valor_f <= 0:
        return None
    return valor_f


def _valor_declarado_mayor_o_igual(datos: dict, valor_referencia: float) -> bool:
    """True si el contribuyente declaro un valor >= al valor de referencia.

    En ese supuesto la base imponible ya coincide con el valor declarado (la
    ley toma el mayor de ambos) y no hay regularizacion al alza por valor de
    referencia que impugnar.
    """
    declarado = datos.get("valor_declarado")
    if declarado is None:
        return False
    try:
        declarado_f = float(declarado)
    except (TypeError, ValueError):
        return False
    return declarado_f >= valor_referencia


def _detectar_tasacion_pericial_contradictoria(
    datos: dict, valor_referencia: float
) -> Optional[dict]:
    """Patron 1: tasacion pericial contradictoria con valor inferior.

    Dispara cuando `tasacion_pericial_contradictoria` es True y existe un
    `valor_pericial` estrictamente menor al valor de referencia.
    """
    if datos.get("tasacion_pericial_contradictoria") is not True:
        return None

    pericial = datos.get("valor_pericial")
    if pericial is None:
        return None
    try:
        pericial_f = float(pericial)
    except (TypeError, ValueError):
        return None
    if pericial_f <= 0 or pericial_f >= valor_referencia:
        return None

    return {
        "tipo": "tasacion_pericial_contradictoria",
        "valor_referencia": valor_referencia,
        "valor_prueba": pericial_f,
        "diferencia": valor_referencia - pericial_f,
    }


def _detectar_informe_tecnico_discrepante(
    datos: dict, valor_referencia: float
) -> Optional[dict]:
    """Patron 2: informe tecnico cualificado con valor inferior.

    Dispara cuando `informe_tecnico_discrepante` es True y existe un
    `valor_informe` estrictamente menor al valor de referencia.
    """
    if datos.get("informe_tecnico_discrepante") is not True:
        return None

    informe = datos.get("valor_informe")
    if informe is None:
        return None
    try:
        informe_f = float(informe)
    except (TypeError, ValueError):
        return None
    if informe_f <= 0 or informe_f >= valor_referencia:
        return None

    return {
        "tipo": "informe_tecnico_discrepante",
        "valor_referencia": valor_referencia,
        "valor_prueba": informe_f,
        "diferencia": valor_referencia - informe_f,
    }


# ---------------------------------------------------------------------------
# Registro de la regla
# ---------------------------------------------------------------------------

@regla(
    id="R025",
    tributos=[Tributo.ITP.value],
    fases=[
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Base imponible ITP por valor de referencia catastral impugnable con "
        "prueba pericial contradictoria o informe tecnico"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — brief no usado por R025
) -> Optional[ArgumentoCandidato]:
    """Evalua R025 sobre el expediente.

    Recorre los documentos en busca del primer acto (liquidacion provisional,
    propuesta de liquidacion o escritura con liquidacion administrativa) en
    el que se aplique el valor de referencia catastral como base imponible y
    exista prueba pericial que acredite valor inferior.

    Returns:
        ArgumentoCandidato | None: candidato si dispara, None si no.
    """
    del brief

    if expediente.tributo != Tributo.ITP:
        return None

    tipos_objetivo = (
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        TipoDocumento.PROPUESTA_LIQUIDACION,
        TipoDocumento.ESCRITURA,
    )

    for doc in expediente.documentos:
        if doc.tipo_documento not in tipos_objetivo:
            continue

        datos = doc.datos or {}
        valor_referencia = _extraer_valor_referencia(datos)
        if valor_referencia is None:
            continue

        if _valor_declarado_mayor_o_igual(datos, valor_referencia):
            continue

        for detector in (
            _detectar_tasacion_pericial_contradictoria,
            _detectar_informe_tecnico_discrepante,
        ):
            disparo = detector(datos, valor_referencia)
            if disparo is None:
                continue

            disparo["documento_id"] = doc.id
            disparo["tipo_documento"] = doc.tipo_documento.value

            return ArgumentoCandidato(
                regla_id="R025",
                descripcion=(
                    "La liquidacion ha fijado la base imponible en el valor "
                    "de referencia catastral cuando el contribuyente dispone "
                    "de prueba pericial cualificada que acredita un valor "
                    "real inferior, lo que habilita la impugnacion "
                    "individualizada expresamente reconocida por la "
                    "jurisprudencia constitucional."
                ),
                cita_normativa_propuesta=_CITA_SEMANTICA,
                datos_disparo=disparo,
                impacto_estimado=(
                    "Minoracion de la base imponible hasta el valor "
                    "acreditado en la prueba pericial, con la consiguiente "
                    "reduccion de la cuota de ITP y, en su caso, de los "
                    "intereses y recargos asociados."
                ),
            )

    return None
