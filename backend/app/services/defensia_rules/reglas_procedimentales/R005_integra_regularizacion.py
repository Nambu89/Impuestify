"""R005 — Principio de integra regularizacion tributaria (T1B-005).

La AEAT, al regularizar la situacion tributaria del obligado, debe computar
no solo los ajustes perjudiciales sino tambien los favorables derivados del
mismo hecho imponible, evitando situaciones de sobreimposicion. La doctrina
del Tribunal Supremo ha elevado este criterio a principio general aplicable
con caracter transversal (IVA, IRPF, IS, ISD, ITP, plusvalia), y el TEAC la
ha consolidado en varias resoluciones recientes.

Casos tipo que dispara esta regla:

- **Denegacion de beneficio fiscal sin ajustes compensatorios**: AEAT niega
  una exencion o deduccion pero no aplica los coeficientes reductores, las
  amortizaciones diferidas, las compensaciones con otros ejercicios, ni
  ajusta pagos a cuenta del mismo hecho.
- **IVA soportado rechazado sin permitir rectificar el repercutido**: caso
  paradigmatico del principio en IVA. AEAT elimina el IVA soportado (perju-
  dica al contribuyente) pero no permite al obligado rectificar el IVA
  repercutido correlativo (que le favorece), situacion que genera doble
  imposicion prohibida por la doctrina TS.

Riesgo alucinacion: **MEDIO**. La cita canonica especifica (STS de 2024 en
regularizacion IVA, TEAC RG 5642/2022 de 23-5-2023, TEAC RG 3226/2023 de
21-6-2023) NO se hardcodea en esta regla — se resuelve en el RAG verificador
contra el corpus de legislacion y jurisprudencia tributaria. Si el RAG no
encuentra soporte con confianza >= 0.7, el candidato se descarta silencio-
samente sin llegar al usuario. Esta regla solo emite la etiqueta semantica
"principio de integra regularizacion tributaria" para que el retriever pueda
localizar la cita canonica adecuada al caso concreto (IVA vs IRPF vs otros).
"""
from __future__ import annotations

from typing import Optional

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
)
from app.services.defensia_rules_engine import regla


# Cita semantica — NUNCA hardcodear "Art. X LGT", "STS", "TEAC RG" aqui.
# El RAG verificador resuelve la referencia canonica especifica.
_CITA_SEMANTICA = (
    "Principio de integra regularizacion tributaria — doctrina del Tribunal "
    "Supremo consolidada y TEAC sobre computo obligatorio de ajustes "
    "favorables al contribuyente en la misma regularizacion"
)

_DOCUMENTOS_RELEVANTES = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


def _dispara_denegacion_beneficio(datos: dict) -> bool:
    """Caso 1: AEAT deniega un beneficio fiscal sin aplicar los ajustes
    compensatorios que el mismo hecho imponible permite a favor del
    contribuyente.
    """
    return bool(datos.get("denegacion_beneficio")) and not bool(
        datos.get("ajustes_compensatorios_aplicados")
    )


def _dispara_iva_sin_rectificacion(datos: dict) -> bool:
    """Caso 2: AEAT rechaza IVA soportado sin permitir al obligado rectificar
    el IVA repercutido correlativo. Caso canonico del principio en IVA.
    """
    return bool(datos.get("iva_soportado_rechazado")) and not bool(
        datos.get("permite_rectificar_repercutido")
    )


@regla(
    id="R005",
    tributos=["IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"],
    fases=[
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "AEAT regulariza sin aplicar el principio de integra regularizacion "
        "(doctrina TS y TEAC consolidada)"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado, brief: Brief
) -> Optional[ArgumentoCandidato]:
    """Evalua si el expediente presenta un supuesto de regularizacion
    incompleta que justifique invocar el principio de integra regularizacion.

    Estrategia: recorre los documentos relevantes (liquidaciones provisiona-
    les y propuestas), analiza los dos casos tipo anteriores y, si alguno se
    cumple, emite un ``ArgumentoCandidato`` con cita semantica generica. El
    tributo concreto del expediente se propaga en ``datos_disparo`` para que
    el RAG verificador pueda filtrar la busqueda por materia (IVA vs IRPF).
    """
    if not expediente.documentos:
        return None

    tributo_str = (
        expediente.tributo.value
        if hasattr(expediente.tributo, "value")
        else str(expediente.tributo)
    )

    doc_disparo = None
    motivo = None

    for doc in expediente.documentos:
        if doc.tipo_documento not in _DOCUMENTOS_RELEVANTES:
            continue
        datos = doc.datos or {}

        if _dispara_denegacion_beneficio(datos):
            doc_disparo = doc
            motivo = "denegacion_beneficio_sin_ajustes_compensatorios"
            break

        if _dispara_iva_sin_rectificacion(datos):
            doc_disparo = doc
            motivo = "iva_soportado_rechazado_sin_rectificacion_repercutido"
            break

    if doc_disparo is None:
        return None

    descripcion = (
        "La Administracion ha regularizado un concepto sin computar los "
        "ajustes favorables al contribuyente derivados del mismo hecho "
        "imponible, vulnerando el principio de integra regularizacion "
        "consolidado por el Tribunal Supremo y el TEAC. Procede solicitar "
        "que la regularizacion sea integra, incluyendo tanto los ajustes "
        "perjudiciales como los favorables."
    )

    return ArgumentoCandidato(
        regla_id="R005",
        descripcion=descripcion,
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo={
            "motivo": motivo,
            "tributo": tributo_str,
            "documento_id": doc_disparo.id,
            "riesgo_alucinacion": "MEDIO",
        },
        impacto_estimado=(
            "Anulacion parcial de la regularizacion para que incluya los "
            "ajustes favorables omitidos; evita situacion de sobreimposicion."
        ),
    )
