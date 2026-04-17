"""R011 — vivienda_habitual_excepcion_separacion (T1B-011).

Regla determinista DefensIA — defensa principal del caso David Oliva.

Dispara cuando concurren estas tres circunstancias sobre un expediente IRPF:

    1. La AEAT ha denegado la exencion por reinversion en vivienda habitual
       (tipicamente en una liquidacion provisional o propuesta de liquidacion)
       por el motivo especifico de no haber cumplido el plazo continuado de
       3 anos de residencia efectiva.

    2. El expediente contiene una sentencia judicial que modifica medidas
       familiares por separacion matrimonial (u otra crisis familiar asimilada).

    3. La residencia efectiva acreditada en la escritura (fecha_adquisicion
       a fecha_transmision) es inferior a 3 anos.

Cuando los tres elementos coinciden, el contribuyente puede alegar la
excepcion del parrafo segundo del art. 41 bis.1 RIRPF, que admite el computo
interrumpido cuando "circunstancias que necesariamente exijan el cambio de
domicilio" (textualmente: separacion matrimonial, traslado laboral, etc.)
obliguen a abandonar la vivienda antes de los 3 anos.

Base normativa (para RAG verificador, NO hardcoded aqui):
    - Art. 41 bis.1 RIRPF (Real Decreto 439/2007), parrafo 2.
    - Concordante art. 38 LIRPF (exencion por reinversion).
    - STS Sala 3.ª 553/2023 de 5-5-2023 (ECLI:ES:TS:2023:1858).
    - Criterio TEAC en reclamaciones por vivienda habitual.

La cita canonica ("Art. 41 bis RIRPF", "STS 553/2023") la resuelve
`defensia_rag_verifier.verify()` contra el corpus normativo — este modulo
devuelve solo una descripcion semantica libre (invariante #2 del plan Parte 2,
anti-alucinacion).

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T1B-011
Caso ground truth: memory/project_session32_defensia_part1.md (David Oliva)
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional

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


# Umbral en dias del plazo de residencia continuada exigido por el parrafo 1.
# 3 anos * 365 dias = 1095. Por encima de este umbral el beneficio aplica sin
# necesidad de acudir a la excepcion del parrafo 2 y R011 no dispara.
_DIAS_PLAZO_3_ANOS: int = 3 * 365

# Tipos de documento donde buscamos la denegacion de la exencion por parte
# de la Administracion tributaria.
_TIPOS_ACTO_AEAT: frozenset[TipoDocumento] = frozenset(
    {
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        TipoDocumento.PROPUESTA_LIQUIDACION,
    }
)

# Motivos de denegacion que caen dentro del alcance de R011. Solo cuando
# AEAT deniega por NO haber cumplido el plazo continuado de 3 anos de
# residencia. Otras denegaciones (reinversion parcial, fuera de plazo de
# reinversion, etc.) requieren otras reglas.
_MOTIVOS_EN_ALCANCE: frozenset[str] = frozenset(
    {
        "residencia_inferior_3_anos",
        "plazo_residencia_incumplido",
        "no_vivienda_habitual_3_anos",
    }
)

# Causas familiares que activan la excepcion del parrafo 2. El extractor
# debe normalizar el valor a una de estas etiquetas.
_CAUSAS_EXCEPCIONALES: frozenset[str] = frozenset(
    {
        "separacion_matrimonial",
        "divorcio",
        "nulidad_matrimonial",
        "disolucion_pareja_hecho",
    }
)


def _parsear_fecha(valor: Any) -> Optional[date]:
    """Convierte un valor heterogeneo (str ISO, datetime, date) a `date`.

    Retorna ``None`` si el valor es ``None``, vacio o no parseable. Nunca
    lanza excepcion — una regla nunca debe poder tumbar el pipeline por un
    dato sucio en el expediente.
    """
    if valor is None or valor == "":
        return None
    if isinstance(valor, datetime):
        return valor.date()
    if isinstance(valor, date):
        return valor
    if isinstance(valor, str):
        try:
            return date.fromisoformat(valor[:10])
        except ValueError:
            return None
    return None


def _buscar_denegacion_en_alcance(
    expediente: ExpedienteEstructurado,
) -> Optional[DocumentoEstructurado]:
    """Localiza el primer acto AEAT que deniegue la exencion por plazo.

    Devuelve el documento si concurren (a) tipo de acto AEAT liquidatorio,
    (b) flag ``deniega_exencion_reinversion=True`` y (c) motivo dentro del
    conjunto de motivos en alcance. Si no hay ninguno, devuelve ``None``.
    """
    for doc in expediente.documentos:
        if doc.tipo_documento not in _TIPOS_ACTO_AEAT:
            continue
        if not doc.datos.get("deniega_exencion_reinversion", False):
            continue
        motivo = doc.datos.get("motivo_denegacion")
        if motivo not in _MOTIVOS_EN_ALCANCE:
            continue
        return doc
    return None


def _buscar_sentencia_familiar(
    expediente: ExpedienteEstructurado,
) -> Optional[DocumentoEstructurado]:
    """Localiza una sentencia judicial que modifique medidas familiares.

    Importante: aunque el phase detector trata `SENTENCIA_JUDICIAL` como
    senal de fase FUERA_DE_ALCANCE (contencioso administrativo), como
    *documento* dentro del expediente es perfectamente valida como prueba
    de la crisis matrimonial. R011 la usa estrictamente en ese rol.
    """
    for doc in expediente.documentos:
        if doc.tipo_documento != TipoDocumento.SENTENCIA_JUDICIAL:
            continue
        if not doc.datos.get("modifica_medidas_familiares", False):
            continue
        causa = doc.datos.get("causa")
        if causa not in _CAUSAS_EXCEPCIONALES:
            continue
        return doc
    return None


def _buscar_escritura_vivienda_habitual(
    expediente: ExpedienteEstructurado,
) -> Optional[DocumentoEstructurado]:
    """Localiza la escritura de la vivienda habitual transmitida."""
    for doc in expediente.documentos:
        if doc.tipo_documento != TipoDocumento.ESCRITURA:
            continue
        if not doc.datos.get("es_vivienda_habitual", False):
            continue
        return doc
    return None


def _dias_residencia(escritura: DocumentoEstructurado) -> Optional[int]:
    """Calcula la residencia efectiva en dias desde la escritura.

    Retorna el numero de dias entre `fecha_adquisicion` y `fecha_transmision`.
    Si faltan fechas o no se pueden parsear, retorna ``None`` para que la
    regla decida no disparar (mejor no argumentar que argumentar en falso).
    """
    adq = _parsear_fecha(escritura.datos.get("fecha_adquisicion"))
    trans = _parsear_fecha(escritura.datos.get("fecha_transmision"))
    if adq is None or trans is None:
        return None
    if trans < adq:
        return None
    return (trans - adq).days


@regla(
    id="R011",
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
        "Vivienda habitual con excepcion del plazo de tres anos por "
        "circunstancias familiares (separacion matrimonial u otra crisis "
        "que exija el cambio de domicilio)."
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,
) -> Optional[ArgumentoCandidato]:
    """Evalua R011 sobre el expediente.

    Flujo:
        1. Verifica que el tributo es IRPF (la excepcion no aplica a otros).
        2. Busca una liquidacion/propuesta AEAT que deniegue la exencion por
           reinversion por incumplimiento del plazo de 3 anos.
        3. Busca una sentencia judicial de modificacion de medidas familiares
           por causa excepcional (separacion, divorcio, etc.).
        4. Busca la escritura de la vivienda habitual y calcula los dias de
           residencia efectiva.
        5. Si la residencia es inferior a 3 anos Y concurren denegacion +
           sentencia, dispara con una descripcion semantica libre.

    Args:
        expediente: expediente estructurado con documentos extraidos.
        brief: brief del usuario (no utilizado por R011, pero parte del
            contrato de todas las reglas).

    Returns:
        ArgumentoCandidato | None: candidato si dispara, None si no.
    """
    del brief  # R011 no depende del brief del usuario.

    # 1. Solo IRPF — el art. 41 bis RIRPF es especifico de IRPF.
    if expediente.tributo != Tributo.IRPF:
        return None

    # 2. Denegacion AEAT en alcance (motivo = plazo de 3 anos).
    acto_denegacion = _buscar_denegacion_en_alcance(expediente)
    if acto_denegacion is None:
        return None

    # 3. Sentencia judicial que pruebe la crisis familiar.
    sentencia = _buscar_sentencia_familiar(expediente)
    if sentencia is None:
        return None

    # 4. Escritura con las fechas reales de residencia.
    escritura = _buscar_escritura_vivienda_habitual(expediente)
    if escritura is None:
        return None

    dias = _dias_residencia(escritura)
    if dias is None:
        return None

    # 5. Si ya se cumplen los 3 anos, la exencion aplica por el parrafo 1
    #    y no hay conflicto que defender — R011 no dispara.
    if dias >= _DIAS_PLAZO_3_ANOS:
        return None

    causa = sentencia.datos.get("causa", "")
    fecha_sentencia = sentencia.datos.get("fecha_sentencia", "")

    return ArgumentoCandidato(
        regla_id="R011",
        descripcion=(
            "La residencia efectiva del contribuyente en la vivienda habitual "
            "transmitida fue inferior al plazo continuado de tres anos exigido "
            "con caracter general, pero existe una sentencia judicial que "
            "modifica las medidas familiares por separacion matrimonial, "
            "circunstancia que, al exigir necesariamente el cambio de "
            "domicilio, permite mantener la consideracion de vivienda "
            "habitual a efectos de la exencion por reinversion."
        ),
        cita_normativa_propuesta=(
            "excepcion al plazo continuado de tres anos de residencia en "
            "vivienda habitual por circunstancias que necesariamente exijan "
            "el cambio de domicilio, tales como separacion matrimonial u "
            "otra crisis familiar acreditada judicialmente"
        ),
        datos_disparo={
            "documento_denegacion_id": acto_denegacion.id,
            "documento_sentencia_id": sentencia.id,
            "documento_escritura_id": escritura.id,
            "causa_excepcional": causa,
            "fecha_sentencia": fecha_sentencia,
            "dias_residencia": dias,
            "dias_plazo_general": _DIAS_PLAZO_3_ANOS,
            "motivo_denegacion": acto_denegacion.datos.get("motivo_denegacion"),
        },
        impacto_estimado=(
            "anulacion de la liquidacion y reconocimiento de la exencion por "
            "reinversion en vivienda habitual"
        ),
    )
