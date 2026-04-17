"""R015 — minimo_personal_familiar.

Regla del Bloque II (IRPF). Dispara cuando la Administracion no aplica
correctamente el minimo personal y familiar del contribuyente: personal,
por descendientes, por ascendientes o por discapacidad. Es especialmente
relevante en supuestos de custodia compartida o exclusiva derivada de una
sentencia de modificacion de medidas.

Fundamento juridico (resuelto por el RAG verificador, no hardcoded aqui):
    - Arts. 56 a 61 LIRPF: minimo personal del contribuyente, minimo por
      descendientes, minimo por ascendientes, minimo por discapacidad y
      normas comunes para la aplicacion del minimo personal y familiar.
    - DGT V2330-19: en custodia compartida, el minimo por descendientes
      se prorratea por partes iguales entre ambos progenitores con
      independencia de con cual convivan efectivamente en cada momento.

Scope del producto (Parte 2 DefensIA):
    - Tributo: IRPF.
    - Fases: todas las fases en las que todavia es util reclamar la
      correcta aplicacion del minimo — comprobacion limitada en sus tres
      momentos (requerimiento, propuesta, post-alegaciones), liquidacion
      firme en plazo de recurso, reposicion y vias TEAR.

Invariante #2 (design Parte 2): la cita normativa devuelta por la regla
es SEMANTICA y libre. La cita canonica (articulo + ley + doctrina DGT)
la resuelve el ``defensia_rag_verifier`` contra el corpus normativo. Por
eso aqui no aparecen literales como "Art. 58 LIRPF" ni "DGT V2330-19".

Relevancia caso David (ground truth del producto):
    Condicional. Tras la sentencia de modificacion de medidas del caso,
    si la custodia resultante es compartida, el minimo por descendientes
    debe prorratearse al 50%/50%. Si AEAT aplica el minimo integro a uno
    solo de los progenitores, R015 dispara. Si la custodia pasa a ser
    exclusiva del usuario, el minimo debe aplicarse al 100% al custodio —
    si AEAT no lo hace, la regla tambien dispara.
"""
from __future__ import annotations

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


# Cita semantica libre — el RAG verificador resuelve la cita canonica. Se
# mantiene como constante para documentar la intencion y facilitar ajustes
# futuros sin tocar la logica de disparo.
_CITA_SEMANTICA = (
    "Aplicacion del minimo personal y familiar (personal, por descendientes, "
    "ascendientes o discapacidad) ajustado a la situacion familiar del "
    "contribuyente"
)


# Tipos de documento en los que pueden venir los flags de aplicacion del
# minimo. La propuesta y la liquidacion provisional son los casos tipicos;
# admitimos tambien ``PROPUESTA_LIQUIDACION`` para cubrir las comprobaciones
# en curso.
_TIPOS_LIQUIDATIVOS = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


def _buscar_doc_liquidativo(
    expediente: ExpedienteEstructurado,
) -> DocumentoEstructurado | None:
    """Devuelve el primer documento liquidativo del expediente, o None.

    La regla necesita un soporte documental donde los flags de aplicacion
    del minimo puedan venir. Si no hay liquidacion ni propuesta en el
    expediente, no hay nada sobre lo que evaluar.
    """
    return next(
        (
            d
            for d in expediente.documentos
            if d.tipo_documento in _TIPOS_LIQUIDATIVOS
        ),
        None,
    )


def _hay_sentencia_modificacion_medidas(
    expediente: ExpedienteEstructurado,
) -> bool:
    """True si el expediente contiene una sentencia judicial de modificacion
    de medidas (o similar) que justifique el analisis de custodia.

    Usamos el campo ``datos.tipo_resolucion`` si existe, pero el hecho de
    que haya un documento ``SENTENCIA_JUDICIAL`` ya es suficiente — el
    caso David muestra que el usuario sube la sentencia precisamente por
    su impacto sobre el minimo por descendientes.
    """
    return any(
        d.tipo_documento == TipoDocumento.SENTENCIA_JUDICIAL
        for d in expediente.documentos
    )


@regla(
    id="R015",
    tributos=[Tributo.IRPF.value],
    fases=[
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        Fase.COMPROBACION_REQUERIMIENTO.value,
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Aplicacion incorrecta o ausencia del minimo personal y familiar "
        "segun arts. 56-61 LIRPF"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R015 sobre el expediente.

    Logica de disparo (primer motivo encontrado gana):

    1. **Custodia compartida sin prorrateo** — si el documento liquidativo
       declara ``custodia="compartida"`` y el flag
       ``minimo_descendientes_aplicado_proporcional`` es False, Y ademas
       el expediente contiene una ``SENTENCIA_JUDICIAL`` que sustente la
       custodia compartida, dispara con motivo
       ``custodia_compartida_sin_prorrateo``.

    2. **Custodia exclusiva sin minimo al custodio** — si el documento
       declara ``custodia="exclusiva"`` con ``progenitor_custodio=True``
       y ``minimo_descendientes_aplicado == 0``, dispara con motivo
       ``custodia_exclusiva_sin_minimo``.

    3. **Discapacidad acreditada sin minimo** — si el documento declara
       ``tiene_discapacidad_33_por_ciento=True`` y
       ``minimo_discapacidad_aplicado == 0``, dispara con motivo
       ``discapacidad_sin_minimo``.

    Si ninguno de los supuestos se cumple, o si no hay documento
    liquidativo en el expediente, devuelve None.

    El filtrado por tributo/fase lo hace el motor antes de invocar esta
    funcion — aqui solo resolvemos la logica material de la regla.
    """
    doc = _buscar_doc_liquidativo(expediente)
    if doc is None:
        # No hay liquidacion ni propuesta — nada que evaluar.
        return None

    datos = doc.datos or {}

    # ---------------------------------------------------------------
    # Motivo 1 — custodia compartida sin prorrateo 50/50
    # ---------------------------------------------------------------
    custodia = str(datos.get("custodia") or "").lower()
    aplicado_proporcional = datos.get(
        "minimo_descendientes_aplicado_proporcional"
    )
    if (
        custodia == "compartida"
        and aplicado_proporcional is False
        and _hay_sentencia_modificacion_medidas(expediente)
    ):
        return ArgumentoCandidato(
            regla_id="R015",
            descripcion=(
                "Tras sentencia judicial con custodia compartida, el minimo "
                "por descendientes debe prorratearse al 50%/50% entre ambos "
                "progenitores. La liquidacion no respeta ese reparto."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "motivo": "custodia_compartida_sin_prorrateo",
                "documento_id": doc.id,
                "tipo_documento": doc.tipo_documento.value,
                "custodia": "compartida",
                "numero_descendientes": datos.get("numero_descendientes"),
            },
            impacto_estimado="alto",
        )

    # ---------------------------------------------------------------
    # Motivo 2 — custodia exclusiva con minimo no aplicado al custodio
    # ---------------------------------------------------------------
    progenitor_custodio = bool(datos.get("progenitor_custodio", False))
    minimo_descendientes_aplicado = datos.get("minimo_descendientes_aplicado")
    if (
        custodia == "exclusiva"
        and progenitor_custodio
        and minimo_descendientes_aplicado is not None
        and float(minimo_descendientes_aplicado) == 0
    ):
        return ArgumentoCandidato(
            regla_id="R015",
            descripcion=(
                "El contribuyente es el progenitor custodio exclusivo, "
                "pero la liquidacion no le aplica el minimo por "
                "descendientes que le corresponde."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "motivo": "custodia_exclusiva_sin_minimo",
                "documento_id": doc.id,
                "tipo_documento": doc.tipo_documento.value,
                "custodia": "exclusiva",
                "numero_descendientes": datos.get("numero_descendientes"),
            },
            impacto_estimado="alto",
        )

    # ---------------------------------------------------------------
    # Motivo 3 — minimo por discapacidad no aplicado
    # ---------------------------------------------------------------
    tiene_discapacidad = bool(
        datos.get("tiene_discapacidad_33_por_ciento", False)
    )
    minimo_discapacidad_aplicado = datos.get("minimo_discapacidad_aplicado")
    if (
        tiene_discapacidad
        and minimo_discapacidad_aplicado is not None
        and float(minimo_discapacidad_aplicado) == 0
    ):
        return ArgumentoCandidato(
            regla_id="R015",
            descripcion=(
                "El contribuyente acredita discapacidad igual o superior al "
                "33%, pero la liquidacion no aplica el minimo por "
                "discapacidad correspondiente."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "motivo": "discapacidad_sin_minimo",
                "documento_id": doc.id,
                "tipo_documento": doc.tipo_documento.value,
                "grado_discapacidad_declarado": datos.get(
                    "grado_discapacidad"
                ),
            },
            impacto_estimado="medio",
        )

    # Ningun supuesto se cumple — la regla no dispara.
    return None
