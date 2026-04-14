"""R012 — anualidades_alimentos_hijos.

Regla sustantiva del bloque IRPF. Dispara cuando la Administracion
regulariza el IRPF de un contribuyente que paga anualidades por alimentos
a favor de sus hijos por decision judicial (o convenio regulador
homologado) SIN aplicar la especialidad tributaria de las escalas
separadas de gravamen.

Fundamento juridico (resuelto por el RAG verificador, no hardcoded aqui):
    - Art. 64 LIRPF: especialidad aplicable a las anualidades por
      alimentos a favor de los hijos — se separa la base liquidable
      general en dos partes para aplicar la escala estatal de gravamen
      (escala A sobre las anualidades, escala B sobre el resto de la
      base). El efecto neto es una reduccion de la cuota integra porque
      ambas porciones tributan con progresividad independiente.
    - Art. 75 LIRPF: misma especialidad aplicada a la escala autonomica
      (o complementaria, segun la terminologia del XSD del Modelo 100).
    - Titulo juridico: la especialidad exige que las anualidades esten
      fijadas por decision judicial — sentencia de divorcio, convenio
      regulador homologado judicialmente o sentencia de modificacion de
      medidas familiares.

Invariante #2 (design Parte 2): la cita normativa devuelta por la regla
es SEMANTICA y libre. La cita canonica ("Arts. 64 y 75 LIRPF") la
resuelve el ``defensia_rag_verifier`` contra el corpus normativo. Por
eso aqui no aparecen literales como "Art. 64" ni "75 LIRPF" — solo
terminos semanticos ("anualidades por alimentos", "escalas separadas
de gravamen", "progenitor no custodio").

Scope del producto (Parte 2 DefensIA):
    - Tributo: IRPF (regla sustantiva — la especialidad solo existe en
      la Ley del IRPF).
    - Fases: LIQUIDACION_FIRME_PLAZO_RECURSO (liquidacion provisional
      notificada y recurrible), COMPROBACION_PROPUESTA / _POST_ALEGACIONES
      (fases previas donde aun se puede alegar la especialidad),
      SANCIONADOR_IMPUESTA (si el no aplicar la especialidad ha generado
      una sancion ligada), REPOSICION_INTERPUESTA y TEAR_*
      (recursos posteriores mientras el acto no sea firme).

Relevancia caso David Oliva (ground truth del producto): la sentencia
de 28-06-2024 modifica medidas familiares. Alta probabilidad de incluir
anualidades por alimentos — por eso la regla se dispara como ajuste
defensivo a favor del contribuyente cuando la liquidacion provisional
de IRPF no aplica las escalas separadas.
"""
from __future__ import annotations

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    Tributo,
    Fase,
    TipoDocumento,
)
from app.services.defensia_rules_engine import regla


# Cita semantica libre — el RAG verificador resuelve la cita canonica.
# Se guarda como constante para documentar la intencion y facilitar
# ajustes futuros sin tocar la logica de disparo.
_CITA_SEMANTICA = (
    "Aplicacion de la especialidad tributaria de anualidades por "
    "alimentos fijadas por decision judicial con escalas separadas de "
    "gravamen"
)


@regla(
    id="R012",
    tributos=[Tributo.IRPF.value],
    fases=[
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        Fase.SANCIONADOR_IMPUESTA.value,
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Aplicacion de la especialidad de anualidades por alimentos "
        "a hijos no aplicada por AEAT"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R012 sobre el expediente.

    Condiciones de disparo (AND logico):

    1. El expediente contiene al menos una ``SENTENCIA_JUDICIAL`` con
       ``datos.incluye_anualidades_alimentos=True`` o
       ``datos.modifica_medidas_familiares=True`` — esto acredita el
       titulo juridico que fija las anualidades.
    2. El expediente contiene una ``LIQUIDACION_PROVISIONAL`` (o, en su
       defecto, una ``PROPUESTA_LIQUIDACION``) con
       ``datos.aplica_escalas_separadas=False`` — AEAT no ha aplicado la
       especialidad en el calculo del IRPF.

    Como fallback de robustez, si la liquidacion no lleva la flag
    ``aplica_escalas_separadas`` pero si marca al contribuyente como
    ``progenitor_no_custodio=True`` y existe una sentencia con
    anualidades, tambien se dispara — es el perfil tipico del pagador
    de anualidades y el writer podra pedir ajuste a AEAT.

    El filtrado por fase ya lo hace el motor antes de invocar esta
    funcion, pero como defensa en profundidad la regla comprueba
    igualmente que exista documentacion coherente.
    """
    # 1) Buscar la sentencia judicial que acredita el titulo juridico
    #    de las anualidades por alimentos. Puede ser una sentencia de
    #    divorcio original o una sentencia de modificacion de medidas
    #    familiares — cualquiera de las dos vale a efectos de R012.
    sentencia = None
    for doc in expediente.documentos:
        if doc.tipo_documento != TipoDocumento.SENTENCIA_JUDICIAL:
            continue
        datos_sentencia = doc.datos or {}
        incluye = bool(datos_sentencia.get("incluye_anualidades_alimentos", False))
        modifica = bool(datos_sentencia.get("modifica_medidas_familiares", False))
        if incluye or modifica:
            sentencia = doc
            break

    if sentencia is None:
        # Sin titulo juridico no hay especialidad que reclamar — nada que
        # hacer. Esto cubre el test "sentencia sin anualidades" (negativo).
        return None

    # Verificamos explicitamente que la sentencia efectivamente incluya
    # anualidades por alimentos. Si solo "modifica medidas" pero no hay
    # anualidades, la regla sigue disparando porque las medidas familiares
    # suelen incluir anualidades y el writer debera confirmarlo con el
    # usuario; pero si el flag ``incluye_anualidades_alimentos`` esta
    # explicitamente en False y ``modifica_medidas_familiares`` tambien,
    # ya habremos salido arriba.
    datos_sentencia = sentencia.datos or {}
    if datos_sentencia.get("incluye_anualidades_alimentos") is False and (
        datos_sentencia.get("modifica_medidas_familiares") is False
    ):
        return None

    # 2) Buscar la liquidacion (o propuesta) que podria no estar aplicando
    #    las escalas separadas. Prioridad: LIQUIDACION_PROVISIONAL >
    #    PROPUESTA_LIQUIDACION.
    tipos_liquidacion = (
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        TipoDocumento.PROPUESTA_LIQUIDACION,
    )
    liquidacion = None
    for tipo in tipos_liquidacion:
        liquidacion = next(
            (d for d in expediente.documentos if d.tipo_documento == tipo),
            None,
        )
        if liquidacion is not None:
            break

    if liquidacion is None:
        # Sin un acto de liquidacion/propuesta no podemos afirmar que
        # AEAT no aplique la especialidad — no disparamos.
        return None

    datos_liquidacion = liquidacion.datos or {}
    aplica_escalas = datos_liquidacion.get("aplica_escalas_separadas")
    progenitor_no_custodio = bool(
        datos_liquidacion.get("progenitor_no_custodio", False)
    )

    # Si AEAT ya aplica las escalas separadas, no hay ajuste que reclamar.
    if aplica_escalas is True:
        return None

    # Condicion principal: la liquidacion NO aplica escalas separadas.
    dispara_principal = aplica_escalas is False
    # Condicion alternativa: la flag no esta presente pero el perfil es
    # el tipico del pagador (progenitor no custodio con sentencia de
    # anualidades). Aceptamos este fallback para cubrir liquidaciones
    # antiguas o mal clasificadas donde el extractor no haya rellenado
    # ``aplica_escalas_separadas``.
    dispara_fallback = aplica_escalas is None and progenitor_no_custodio

    if not (dispara_principal or dispara_fallback):
        return None

    descripcion = (
        "La Administracion regulariza el IRPF sin aplicar la especialidad "
        "tributaria de las anualidades por alimentos fijadas por decision "
        "judicial — deben aplicarse escalas separadas de gravamen sobre la "
        "parte de la base liquidable correspondiente a las anualidades y "
        "sobre el resto, respectivamente, lo que reduce la progresividad y "
        "por tanto la cuota integra del contribuyente."
    )

    return ArgumentoCandidato(
        regla_id="R012",
        descripcion=descripcion,
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo={
            "sentencia_id": sentencia.id,
            "sentencia_incluye_anualidades": datos_sentencia.get(
                "incluye_anualidades_alimentos"
            ),
            "sentencia_modifica_medidas": datos_sentencia.get(
                "modifica_medidas_familiares"
            ),
            "liquidacion_id": liquidacion.id,
            "tipo_liquidacion": liquidacion.tipo_documento.value,
            "aplica_escalas_separadas": aplica_escalas,
            "progenitor_no_custodio": progenitor_no_custodio,
        },
        impacto_estimado="alto",
    )
