"""R001 — motivacion_insuficiente (T1B-001).

Regla determinista DefensIA. Dispara cuando un acto administrativo tributario
(liquidacion provisional, propuesta de liquidacion, requerimiento, sancion o
acto impugnado en reposicion/TEAR) no motiva suficientemente su contenido:

    - No incluye fundamentos de derecho, o
    - Usa motivacion "por remision" a otro acto previo que NO ha sido
      notificado al contribuyente (doctrina TEAC reiterada).

Base normativa (para RAG verificador, NO hardcoded aqui):
    - Art. 102.2.c) LGT (Ley 58/2003).
    - Concordante art. 35.1.a) y 88.3 Ley 39/2015.
    - STS Sala 3.ª 1695/2024 de 29-10-2024.
    - STS de 5-4-2024 (rec. 96/2023).
    - Doctrina reiterada TEAC sobre motivacion "por remision".

La cita canonica ("Art. 102.2.c LGT") la resuelve `defensia_rag_verifier.verify()`
contra el corpus normativo — este modulo devuelve solo una descripcion
semantica libre (invariante #2 del plan Parte 2, anti-alucinacion).

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T1B-001
Research: C:/tmp/research.md §R001
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


# Tipos de documento sobre los que la regla busca carencias de motivacion.
# Solo actos administrativos de la Administracion tributaria — los escritos
# del propio usuario obviamente no se someten a este test.
_TIPOS_MOTIVABLES: frozenset[TipoDocumento] = frozenset(
    {
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        TipoDocumento.PROPUESTA_LIQUIDACION,
        TipoDocumento.REQUERIMIENTO,
        TipoDocumento.ACUERDO_INICIO_SANCIONADOR,
        TipoDocumento.PROPUESTA_SANCION,
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
    }
)


def _motivo_de_disparo(datos: dict) -> Optional[str]:
    """Analiza los `datos` de un documento y devuelve el motivo de disparo.

    Retorna:
        - "sin_fundamentos_derecho" si el acto no contiene fundamentos de derecho.
        - "remision_sin_acto_previo" si usa motivacion por remision y el acto
          previo no ha sido notificado al contribuyente.
        - None si la motivacion es suficiente (no dispara).

    Defaults conservadores: si una clave no esta presente asumimos que SI hay
    motivacion (benefit of the doubt). Solo disparamos cuando el extractor ha
    afirmado explicitamente la carencia.
    """
    tiene_fundamentos = datos.get("tiene_fundamentos_derecho", True)
    if tiene_fundamentos is False:
        return "sin_fundamentos_derecho"

    motivacion_por_remision = datos.get("motivacion_por_remision", False)
    if motivacion_por_remision is True:
        acto_previo_notificado = datos.get("acto_previo_notificado", True)
        if acto_previo_notificado is False:
            return "remision_sin_acto_previo"

    return None


@regla(
    id="R001",
    tributos=[
        Tributo.IRPF,
        Tributo.IVA,
        Tributo.ISD,
        Tributo.ITP,
        Tributo.PLUSVALIA,
    ],
    fases=[
        # Fases del enum real `app.models.defensia.Fase` donde esta regla
        # tiene sentido. Los nombres del research ("LIQUIDACION_PROVISIONAL",
        # "PROPUESTA_LIQUIDACION", "SANCION", "REQUERIMIENTO", "REPOSICION",
        # "TEAR_*") se mapean al enum real a continuacion.
        Fase.COMPROBACION_REQUERIMIENTO,
        Fase.COMPROBACION_PROPUESTA,
        Fase.COMPROBACION_POST_ALEGACIONES,
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO,
        Fase.SANCIONADOR_INICIADO,
        Fase.SANCIONADOR_PROPUESTA,
        Fase.SANCIONADOR_IMPUESTA,
        Fase.REPOSICION_INTERPUESTA,
        Fase.TEAR_INTERPUESTA,
        Fase.TEAR_AMPLIACION_POSIBLE,
    ],
    descripcion=(
        "Liquidacion, propuesta, requerimiento o sancion sin motivacion "
        "suficiente conforme a la obligacion de expresar hechos y "
        "fundamentos de derecho del acto administrativo tributario."
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,
) -> Optional[ArgumentoCandidato]:
    """Evalua R001 sobre el expediente.

    Recorre los documentos del expediente en busca del primer acto
    administrativo tributario cuya motivacion sea insuficiente. Si lo
    encuentra, devuelve un `ArgumentoCandidato` con descripcion semantica
    libre. Si no hay ningun documento con carencia detectada, devuelve
    `None` y la regla no se incluye en el dictamen.

    Args:
        expediente: el expediente estructurado con la lista de documentos
            extraidos y clasificados.
        brief: el brief del usuario (no utilizado por R001, pero parte del
            contrato de todas las reglas).

    Returns:
        ArgumentoCandidato | None: candidato si dispara, None si no.
    """
    del brief  # R001 no depende del brief del usuario.

    for doc in expediente.documentos:
        if doc.tipo_documento not in _TIPOS_MOTIVABLES:
            continue

        motivo = _motivo_de_disparo(doc.datos)
        if motivo is None:
            continue

        return ArgumentoCandidato(
            regla_id="R001",
            descripcion=(
                "El acto administrativo impugnado carece de motivacion "
                "suficiente: no identifica con el detalle exigible los hechos "
                "y fundamentos de derecho que justifican el rechazo de la "
                "autoliquidacion del contribuyente."
            ),
            cita_normativa_propuesta=(
                "Motivacion insuficiente del acto administrativo tributario — "
                "obligacion de expresar hechos determinantes y fundamentos "
                "de derecho, incluyendo el caso de motivacion por remision "
                "a acto previo no notificado al contribuyente."
            ),
            datos_disparo={
                "motivo": motivo,
                "documento_id": doc.id,
                "tipo_documento": doc.tipo_documento.value,
            },
            impacto_estimado="anulabilidad del acto por defecto de motivacion",
        )

    return None
