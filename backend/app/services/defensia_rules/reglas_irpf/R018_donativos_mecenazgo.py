"""R018 — donativos_mecenazgo (T1B-018).

Regla del Bloque II (IRPF). Dispara cuando AEAT admite parcialmente o deniega
una deduccion por donativos declarada por el contribuyente existiendo un
certificado valido emitido por una entidad beneficiaria del regimen fiscal
de mecenazgo, o cuando una donacion recurrente (misma entidad durante al
menos tres anos consecutivos) no ha visto aplicado el porcentaje incrementado.

Fundamento juridico (resuelto por el RAG verificador, NO hardcoded aqui):
    - Art. 68.3 LIRPF: deduccion por donativos en cuota integra estatal.
    - Ley 49/2002 (arts. 17-20): regimen fiscal de entidades sin fines
      lucrativos y de los incentivos al mecenazgo.
    - Ley 7/2024 (disposicion adicional): nuevos porcentajes aplicables a
      partir de 2024 — 80% sobre los primeros 250 EUR y 40% sobre el
      exceso, con elevacion al 45% cuando el contribuyente haya donado a
      la misma entidad durante al menos dos ejercicios anteriores por
      importe igual o superior (donacion recurrente).
    - Requisito formal: certificado emitido por la entidad donataria con
      el contenido del art. 24 Ley 49/2002.

Scope del producto (Parte 2 DefensIA):
    - Tributo: IRPF (la deduccion aplica exclusivamente en este tributo).
    - Fases: LIQUIDACION_FIRME_PLAZO_RECURSO, COMPROBACION_PROPUESTA,
      COMPROBACION_POST_ALEGACIONES, REPOSICION_INTERPUESTA, TEAR_*.

Invariante #2 (design Parte 2): la cita normativa devuelta por la regla es
SEMANTICA y libre. La cita canonica (Art. 68.3 LIRPF / Ley 49/2002) la
resuelve ``defensia_rag_verifier`` contra el corpus normativo. Por eso aqui
no aparecen literales como "Art. 68.3 LIRPF" ni "Ley 49/2002" — solo
terminos semanticos ("donativo", "mecenazgo", "certificado", "recurrencia").
"""
from __future__ import annotations

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    TipoDocumento,
)
from app.services.defensia_rules_engine import regla


# Tipos de documento que pueden contener los campos estructurados de
# donativo declarado / deduccion admitida. Se incluye OTROS para que el
# extractor pueda adjuntar certificados de donacion aunque el documento
# no sea directamente una liquidacion.
_TIPOS_CON_DATOS_DONATIVO = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
    TipoDocumento.OTROS,
)

# Cita semantica libre — el RAG verificador resuelve la cita canonica.
_CITA_SEMANTICA = (
    "Deduccion por donativos a entidades beneficiarias del regimen fiscal "
    "de mecenazgo con certificado emitido por la entidad donataria, "
    "incluyendo elevacion por donacion recurrente"
)


@regla(
    id="R018",
    tributos=["IRPF"],
    fases=[
        "LIQUIDACION_FIRME_PLAZO_RECURSO",
        "COMPROBACION_PROPUESTA",
        "COMPROBACION_POST_ALEGACIONES",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    ],
    descripcion=(
        "Denegacion o admision parcial indebida de deduccion por donativos "
        "a entidades beneficiarias del mecenazgo con certificado valido"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R018 sobre el expediente.

    La regla inspecciona el primer documento de liquidacion o propuesta que
    contenga datos de donativos y comprueba tres escenarios de disparo:

    1. **Denegacion integra con certificado**: ``deduccion_admitida == 0`` y
       ``donativo_declarado > 0`` con ``certificado_donacion_presentado``
       en ``True``. AEAT rechaza el beneficio pese a cumplirse el requisito
       formal constitutivo.
    2. **Admision parcial**: ``deduccion_admitida < deduccion_calculada_teorica``
       con certificado. La Administracion reconoce el donativo pero aplica
       un importe inferior al que resulta de los porcentajes legales.
    3. **Recurrencia sin elevacion al 45%**: la donacion es recurrente
       (3 anos consecutivos a la misma entidad) y el porcentaje aplicado
       sobre el exceso de 250 EUR es 40% en lugar del 45% incrementado
       introducido por la Ley 7/2024.

    En cualquier otro caso (sin certificado, deduccion correcta, ausencia
    de documento relevante) la regla devuelve ``None``.

    El filtrado por tributo/fase lo hace el motor antes de invocar esta
    funcion — aqui solo hacemos defensa en profundidad leyendo los datos
    estructurados de los documentos.
    """
    # Tomamos el primer documento que tenga datos de donativo. El filtrado
    # por tipo evita leer accidentalmente datos de documentos sancionadores
    # u otros que no contengan los campos esperados.
    doc_donativo = next(
        (
            d
            for d in expediente.documentos
            if d.tipo_documento in _TIPOS_CON_DATOS_DONATIVO
            and (d.datos or {}).get("donativo_declarado") is not None
        ),
        None,
    )
    if doc_donativo is None:
        return None

    datos = doc_donativo.datos or {}

    donativo_declarado = float(datos.get("donativo_declarado") or 0.0)
    tiene_certificado = bool(datos.get("certificado_donacion_presentado", False))
    deduccion_admitida = datos.get("deduccion_admitida")
    deduccion_teorica = datos.get("deduccion_calculada_teorica")
    recurrencia_3 = bool(datos.get("donacion_recurrente_3_anos", False))
    porcentaje_aplicado = datos.get("porcentaje_aplicado")

    # Requisito formal: sin certificado no hay deduccion legalmente
    # defendible. La regla NO debe disparar aunque AEAT haya denegado
    # porque el defecto es del contribuyente, no del acto administrativo.
    if not tiene_certificado:
        return None

    if donativo_declarado <= 0:
        return None

    # Escenario 1 — denegacion integra con certificado valido.
    if deduccion_admitida is not None and float(deduccion_admitida) == 0.0:
        return ArgumentoCandidato(
            regla_id="R018",
            descripcion=(
                "La Administracion deniega integramente la deduccion por "
                "donativo pese a aportarse certificado valido emitido por "
                "la entidad donataria beneficiaria del regimen fiscal de "
                "mecenazgo."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "motivo": "denegacion_integra_con_certificado",
                "documento_id": doc_donativo.id,
                "donativo_negado": donativo_declarado,
                "tiene_certificado": True,
            },
            impacto_estimado="medio",
        )

    # Escenario 2 — admision parcial con delta respecto a la teorica.
    if (
        deduccion_admitida is not None
        and deduccion_teorica is not None
        and float(deduccion_admitida) < float(deduccion_teorica)
    ):
        delta = float(deduccion_teorica) - float(deduccion_admitida)
        return ArgumentoCandidato(
            regla_id="R018",
            descripcion=(
                "La Administracion admite parcialmente la deduccion por "
                "donativo a entidad beneficiaria del mecenazgo aplicando un "
                "importe inferior al que resulta de los porcentajes legales "
                "sobre el donativo acreditado con certificado."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "motivo": "admision_parcial",
                "documento_id": doc_donativo.id,
                "donativo_declarado": donativo_declarado,
                "deduccion_teorica": float(deduccion_teorica),
                "deduccion_admitida": float(deduccion_admitida),
                "delta_deduccion": round(delta, 2),
                "tiene_certificado": True,
            },
            impacto_estimado="medio",
        )

    # Escenario 3 — recurrencia 3 anos sin elevacion al 45%.
    if recurrencia_3 and porcentaje_aplicado is not None:
        porcentaje = float(porcentaje_aplicado)
        if porcentaje < 0.45:
            return ArgumentoCandidato(
                regla_id="R018",
                descripcion=(
                    "La donacion acreditada con certificado es recurrente "
                    "a la misma entidad durante tres anos consecutivos y "
                    "procede la elevacion del porcentaje aplicable al "
                    "exceso de la base, pero la Administracion ha aplicado "
                    "un porcentaje inferior al incrementado legalmente."
                ),
                cita_normativa_propuesta=_CITA_SEMANTICA,
                datos_disparo={
                    "motivo": "recurrencia_sin_elevacion",
                    "documento_id": doc_donativo.id,
                    "donativo_declarado": donativo_declarado,
                    "porcentaje_aplicado": porcentaje,
                    "tiene_certificado": True,
                    "recurrencia_3_anos": True,
                },
                impacto_estimado="bajo",
            )

    return None
