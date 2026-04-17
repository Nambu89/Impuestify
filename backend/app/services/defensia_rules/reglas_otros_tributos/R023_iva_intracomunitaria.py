"""R023 — iva_intracomunitaria (T1B-023).

Regla del Bloque III (otros tributos, IVA). Modela la exencion de las
entregas intracomunitarias de bienes (EIB) del art. 25 LIVA, en relacion
con el regimen de adquisiciones intracomunitarias (AIB) del art. 15 LIVA,
leidos a la luz de la doctrina del Tribunal de Justicia de la Union
Europea en el asunto C-146/05 Collee: los requisitos formales (inclusion
del NIF-IVA del adquirente en el censo VIES, correcta declaracion de la
operacion en el modelo 349) NO pueden prevalecer sobre los requisitos
materiales (transporte efectivo al territorio de otro Estado miembro y
condicion de empresario o profesional del destinatario) cuando estos
ultimos estan plenamente acreditados.

La regla dispara cuando la AEAT:

    - Deniega la exencion de una EIB porque el NIF-IVA del adquirente no
      constaba en VIES en el momento de la operacion, pese a que el
      transporte a otro Estado miembro esta acreditado y el destinatario
      es empresario o profesional.
    - Deniega la exencion por un error formal en el modelo 349 (omision,
      diferencia de importe, periodo incorrecto) cuando los requisitos
      materiales estan igualmente acreditados.

La regla NO dispara cuando:

    - No se acredita transporte efectivo al territorio de otro Estado
      miembro: el requisito material falla y la denegacion es legitima.
    - El destinatario no es empresario o profesional identificado en la
      UE: decae la estructura B2B que habilita la exencion del art. 25.
    - La AEAT no ha denegado la exencion de la EIB en el documento (no
      hay conflicto sobre el que construir la defensa).

Invariante #2 (anti-alucinacion): la cita normativa devuelta por la regla
es SEMANTICA y libre. La cita canonica (articulo + ley + STJUE) la
resuelve el ``defensia_rag_verifier`` contra el corpus normativo. Por eso
aqui no aparecen literales como "Art. 25 LIVA", "STJUE C-146/05" ni
"Collee" — solo terminos semanticos descriptivos del supuesto.
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


# Cita semantica libre — el RAG verificador resuelve la cita canonica.
_CITA_SEMANTICA = (
    "Exencion de entregas intracomunitarias de bienes cuando se acreditan "
    "los requisitos materiales de transporte efectivo al territorio de "
    "otro Estado miembro y condicion de empresario del destinatario, "
    "conforme a la doctrina del Tribunal de Justicia de la Union Europea "
    "sobre prevalencia de la sustancia sobre la forma"
)


# Tipos de documento relevantes para la regla. La denegacion de la exencion
# aparece normalmente en la liquidacion o propuesta de liquidacion del
# procedimiento de comprobacion limitada / verificacion de datos sobre IVA.
_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


# ---------------------------------------------------------------------------
# Regla
# ---------------------------------------------------------------------------

@regla(
    id="R023",
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
        "Denegacion de exencion intracomunitaria por incumplimiento formal "
        "con requisitos materiales acreditados (doctrina TJUE sustancia "
        "sobre forma)"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R023 sobre el expediente.

    Se recorren los documentos del expediente en orden buscando una
    liquidacion o propuesta en la que AEAT haya denegado la exencion del
    art. 25 LIVA. Para que la regla dispare se exige simultaneamente:

    1. ``denegacion_exencion_EIB`` es True — AEAT rechazo expresamente la
       exencion.
    2. ``transporte_efectivo_acreditado`` es True — el requisito material
       de transporte intracomunitario esta acreditado (CMR, carta de porte,
       prueba logistica suficiente).
    3. ``destinatario_empresario_UE`` es True — el adquirente es empresario
       o profesional de otro Estado miembro (requisito material B2B).
    4. Existe un defecto formal: ``nif_vies_ausente`` o
       ``error_modelo_349``. Al menos uno de los dos debe ser True. Si
       ninguno lo es, la denegacion responde a otra causa y R023 no es la
       regla correcta (aunque la estructura material encaje).

    Si ninguna liquidacion satisface el patron, la funcion devuelve
    ``None``. El filtrado por tributo/fase lo realiza el motor antes de
    invocar esta funcion.
    """
    for doc in expediente.documentos:
        if doc.tipo_documento not in _TIPOS_LIQUIDACION:
            continue

        datos = doc.datos or {}

        denegacion = bool(datos.get("denegacion_exencion_EIB", False))
        if not denegacion:
            continue

        transporte_ok = bool(datos.get("transporte_efectivo_acreditado", False))
        destinatario_ok = bool(datos.get("destinatario_empresario_UE", False))

        if not transporte_ok or not destinatario_ok:
            # Algun requisito material no se acredita: la doctrina Collee
            # NO es aplicable y la denegacion de la exencion es legitima.
            continue

        nif_vies_ausente = bool(datos.get("nif_vies_ausente", False))
        error_349 = bool(datos.get("error_modelo_349", False))

        if not (nif_vies_ausente or error_349):
            # Los requisitos materiales estan acreditados pero no consta un
            # defecto formal en VIES ni en el modelo 349: la denegacion
            # responde a otra causa (p.ej. falta de transporte, operacion
            # simulada). R023 no es la regla adecuada.
            continue

        return ArgumentoCandidato(
            regla_id="R023",
            descripcion=(
                "La Administracion deniega la exencion de una entrega "
                "intracomunitaria de bienes basandose en un incumplimiento "
                "formal (ausencia del adquirente en VIES o error en el "
                "modelo 349) pese a constar acreditados los requisitos "
                "materiales de transporte efectivo al territorio de otro "
                "Estado miembro y condicion de empresario o profesional "
                "del destinatario. La doctrina del Tribunal de Justicia "
                "de la Union Europea exige hacer prevalecer la sustancia "
                "sobre la forma en estos supuestos."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "tipo": "exencion_EIB_denegada_por_forma",
                "documento_id": doc.id,
                "tipo_documento": doc.tipo_documento.value,
                "nif_vies_ausente": nif_vies_ausente,
                "error_modelo_349": error_349,
                "transporte_efectivo_acreditado": transporte_ok,
                "destinatario_empresario_UE": destinatario_ok,
                "ejercicio": datos.get("ejercicio"),
            },
            impacto_estimado="alto",
        )

    return None
