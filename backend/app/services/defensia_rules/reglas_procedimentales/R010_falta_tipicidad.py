"""R010 — falta_tipicidad_o_norma_inaplicable (T1B-010).

Regla del Bloque I (procedimentales). Dispara cuando el acuerdo de imposicion
de sancion imputa una conducta que NO encaja en el tipo infractor citado
(arts. 191-206 LGT) o cuando la Administracion aplica analogicamente un tipo
sancionador a un supuesto no previsto expresamente por la norma.

Fundamento juridico (resuelto por el RAG verificador, no hardcoded aqui):
    - Art. 178 LGT: principios de la potestad sancionadora tributaria
      (legalidad, tipicidad, responsabilidad, proporcionalidad, no
      concurrencia, irretroactividad).
    - Art. 183.1 LGT: la infraccion tributaria debe estar tipificada y
      sancionada en la Ley — exige predeterminacion normativa suficiente
      de la conducta.
    - Art. 25.1 CE: principio de legalidad sancionadora.
    - STC 2/2003 y jurisprudencia constitucional sobre tipicidad estricta:
      prohibicion de interpretacion extensiva y analogia in peius en
      materia sancionadora.

Scope del producto (Parte 2 DefensIA):
    - Tributos: IRPF, IVA, ISD, ITP, Plusvalia Municipal (transversal
      sancionador).
    - Fases: SANCIONADOR_IMPUESTA (el acuerdo ya esta notificado y el
      contribuyente puede recurrir), REPOSICION_INTERPUESTA y TEAR_*
      (la regla sigue siendo util mientras la sancion no sea firme).
      Tambien las fases sancionador previas (INICIADO, PROPUESTA) cuando
      el expediente ya permita identificar el tipo infractor citado.

Invariante #2 (design Parte 2): la cita normativa devuelta por la regla
es SEMANTICA y libre. La cita canonica (articulo + ley + jurisprudencia)
la resuelve el ``defensia_rag_verifier`` contra el corpus normativo. Por
eso aqui no aparecen literales como "Art. 183.1 LGT" ni "STC 2/2003" —
solo terminos semanticos ("tipicidad", "infraccion", "predeterminacion").
"""
from __future__ import annotations

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    TipoDocumento,
)
from app.services.defensia_rules_engine import regla


# Cita semantica libre — el RAG verificador resuelve la cita canonica. Se
# guarda como constante para documentar la intencion y facilitar ajustes
# futuros sin tocar la logica de disparo.
_CITA_SEMANTICA = (
    "Falta de tipicidad estricta en la infraccion imputada o aplicacion "
    "analogica de tipos sancionadores"
)


@regla(
    id="R010",
    tributos=["IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"],
    fases=[
        "SANCIONADOR_INICIADO",
        "SANCIONADOR_PROPUESTA",
        "SANCIONADOR_IMPUESTA",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    ],
    descripcion=(
        "Falta de tipicidad estricta en la infraccion imputada "
        "(principios de legalidad y tipicidad del ordenamiento sancionador)"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R010 sobre el expediente.

    La funcion busca un documento de tipo ``ACUERDO_IMPOSICION_SANCION``
    (o, subsidiariamente, ``PROPUESTA_SANCION`` / ``ACUERDO_INICIO_SANCIONADOR``)
    y comprueba dos flags en ``datos``:

    - ``conducta_no_encaja_en_tipo``: la conducta imputada no encaja en el
      tipo infractor citado.
    - ``aplicacion_analogica``: la Administracion aplica analogicamente un
      tipo sancionador a un supuesto no previsto.

    Si al menos uno de los dos flags es ``True``, la regla devuelve un
    ``ArgumentoCandidato``. En caso contrario (o si no hay documento
    sancionador en el expediente) devuelve ``None``.

    El filtrado por fase ya lo hace el motor antes de invocar esta funcion,
    pero como defensa en profundidad la regla comprueba igualmente que al
    menos un documento sea de tipo sancionador — esto evita falsos
    positivos en expedientes donde el usuario haya clasificado mal la fase.
    """
    # Tipos de documento que pueden disparar la regla, en orden de preferencia.
    tipos_sancionador = (
        TipoDocumento.ACUERDO_IMPOSICION_SANCION,
        TipoDocumento.PROPUESTA_SANCION,
        TipoDocumento.ACUERDO_INICIO_SANCIONADOR,
    )

    doc_sancion = next(
        (d for d in expediente.documentos if d.tipo_documento in tipos_sancionador),
        None,
    )
    if doc_sancion is None:
        # No hay documento sancionador en el expediente — nada que tipificar.
        return None

    datos = doc_sancion.datos or {}
    conducta_no_encaja = bool(datos.get("conducta_no_encaja_en_tipo", False))
    aplicacion_analogica = bool(datos.get("aplicacion_analogica", False))

    if not (conducta_no_encaja or aplicacion_analogica):
        return None

    # Prioridad del motivo: conducta_no_encaja gana si ambos son True, porque
    # es el defecto estructural mas grave (el tipo no se proyecta sobre el
    # hecho). La analogia es un defecto de metodo interpretativo.
    if conducta_no_encaja:
        motivo = "conducta_no_encaja_en_tipo"
    else:
        motivo = "aplicacion_analogica"

    return ArgumentoCandidato(
        regla_id="R010",
        descripcion=(
            "La Administracion imputa una infraccion que no esta "
            "predeterminada normativamente con suficiente claridad "
            "(tipicidad estricta) o se aplica analogicamente un tipo "
            "sancionador a un supuesto no previsto."
        ),
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo={
            "motivo": motivo,
            "documento_id": doc_sancion.id,
            "tipo_documento": doc_sancion.tipo_documento.value,
            "tipo_infractor_citado": datos.get("tipo_infractor_citado"),
        },
        impacto_estimado="alto",
    )
