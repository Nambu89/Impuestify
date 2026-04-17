"""R016 — imputacion_rentas_inmuebles (T1B-016).

Regla del Bloque II (IRPF). Dispara cuando AEAT imputa una renta inmobiliaria
(art. 85 LIRPF, 2% o 1,1% sobre valor catastral) sobre un inmueble que:

1. Fue vivienda habitual del contribuyente durante (todo o parte de) el
   periodo impositivo. La vivienda habitual esta expresamente EXCLUIDA de la
   imputacion por el art. 85 LIRPF.
2. Estuvo afecto a una actividad economica — igualmente excluido por el
   art. 85 LIRPF (los bienes afectos generan rendimientos de actividades
   economicas, no rentas imputadas).
3. Estuvo a disposicion del titular solo una fraccion de dias del ejercicio
   (por ejemplo, tras una adquisicion o transmision intra-ejercicio, o por
   cambio de uso/afectacion) sin que AEAT prorratee la cuantia imputada por
   los dias efectivos de disposicion.

Relevancia caso David: condicional. Si AEAT, al denegar el caracter de
vivienda habitual, imputa renta por los ~2 anos 5 meses que David residio en
el inmueble, la imputacion hay que impugnarla — o bien porque fue vivienda
habitual durante esa fraccion, o bien porque el calculo no prorratea por
dias a disposicion.

Fundamento juridico (resuelto por el RAG verificador, no hardcoded aqui):
    - Art. 85 LIRPF: regulacion positiva de la imputacion de rentas
      inmobiliarias, exclusiones (vivienda habitual, suelo no edificado,
      afectos a actividad, en construccion, imposibles de uso por razones
      urbanisticas) y clausula de prorrateo por dias de disposicion.

Scope del producto (Parte 2 DefensIA):
    - Tributo: IRPF exclusivamente — la imputacion de rentas inmobiliarias
      es una figura especifica del IRPF (art. 85 LIRPF); no existe en IVA,
      ISD, ITP ni Plusvalia Municipal.
    - Fases: LIQUIDACION_FIRME_PLAZO_RECURSO, COMPROBACION_PROPUESTA,
      COMPROBACION_POST_ALEGACIONES, REPOSICION_INTERPUESTA,
      TEAR_INTERPUESTA, TEAR_AMPLIACION_POSIBLE. En fases sancionadoras no
      aplica (un eventual defecto de tipicidad sobre la imputacion se
      canaliza por R010, no por R016).

Invariante #2 (design Parte 2): la cita normativa devuelta por la regla es
SEMANTICA y libre. La cita canonica (`Art. 85 LIRPF`) la resuelve el
``defensia_rag_verifier`` contra el corpus normativo. Por eso aqui no
aparecen literales como "Art. 85 LIRPF" ni variantes — solo terminos
semanticos ("imputacion", "rentas inmobiliarias", "vivienda habitual",
"prorrateo", "dias de disposicion").
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
# sin tocar la logica de disparo. No debe contener literales de articulos.
_CITA_SEMANTICA = (
    "Imputacion de rentas inmobiliarias sobre inmueble no sujeto o sin "
    "prorrateo por los dias de disponibilidad del titular"
)

# Dias del ejercicio fiscal estandar. No se hardcodea el anio natural 365
# como invariante normativa — se usa solo para calcular ``dias_no_prorrateados``
# a efectos del ``datos_disparo`` que el writer expondra al usuario.
_DIAS_EJERCICIO = 365


@regla(
    id="R016",
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
        "Imputacion de rentas inmobiliarias incorrecta sobre inmueble "
        "excluido (vivienda habitual o afecto a actividad) o sin prorrateo "
        "por dias a disposicion del titular"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R016 sobre el expediente.

    La funcion busca un documento de tipo ``LIQUIDACION_PROVISIONAL`` o
    ``PROPUESTA_LIQUIDACION`` (subsidiariamente ``ESCRITURA`` si aportan
    datos de imputacion) y verifica los triggers descritos en el docstring
    del modulo:

    1. Precondicion: ``datos.imputa_renta_inmueble`` debe ser ``True``. Si
       AEAT no esta imputando renta, la regla no tiene nada que impugnar.
    2. Al menos uno de los siguientes motivos debe concurrir:
       a. ``datos.es_vivienda_habitual_en_periodo=True``
       b. ``datos.afecto_actividad_economica=True``
       c. ``datos.prorrateo_por_dias_aplicado=False`` con
          ``datos.dias_a_disposicion`` < 365 (prorrateo omitido).

    Si ninguno concurre, la imputacion se considera correctamente aplicada
    y la regla devuelve ``None``.

    El motivo se prioriza en el orden (a) > (b) > (c). Cuando (c) dispara,
    ``datos_disparo`` expone ``dias_no_prorrateados`` = 365 - dias_a_disposicion
    para que el writer lo use en el escrito.
    """
    # Tipos de documento que pueden disparar la regla. Preferimos los actos
    # administrativos donde AEAT expresa la imputacion; la ESCRITURA queda
    # como fallback por si el extractor adjunta ahi los datos catastrales.
    tipos_liquidacion = (
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        TipoDocumento.PROPUESTA_LIQUIDACION,
        TipoDocumento.ESCRITURA,
    )

    doc = next(
        (d for d in expediente.documentos if d.tipo_documento in tipos_liquidacion),
        None,
    )
    if doc is None:
        return None

    datos = doc.datos or {}

    # Precondicion: AEAT debe estar imputando renta inmobiliaria. Sin esta
    # flag, cualquier otro dato del extractor es irrelevante a efectos de
    # esta regla.
    if not bool(datos.get("imputa_renta_inmueble", False)):
        return None

    vivienda_habitual = bool(datos.get("es_vivienda_habitual_en_periodo", False))
    afecto_actividad = bool(datos.get("afecto_actividad_economica", False))
    prorrateo_aplicado = bool(datos.get("prorrateo_por_dias_aplicado", True))
    dias_a_disposicion = datos.get("dias_a_disposicion")

    # Caso (c): prorrateo omitido. Solo cuenta como disparo si efectivamente
    # hay menos de 365 dias a disposicion (caso contrario, aunque el flag
    # este a False, el prorrateo seria innecesario y no hay agravio).
    try:
        dias_a_disposicion_int = (
            int(dias_a_disposicion) if dias_a_disposicion is not None else None
        )
    except (TypeError, ValueError):
        dias_a_disposicion_int = None

    sin_prorrateo = (
        (not prorrateo_aplicado)
        and dias_a_disposicion_int is not None
        and 0 <= dias_a_disposicion_int < _DIAS_EJERCICIO
    )

    if not (vivienda_habitual or afecto_actividad or sin_prorrateo):
        return None

    # Priorizacion de motivos (ver docstring). Un solo ArgumentoCandidato por
    # invocacion — el motor agrega los candidatos de todas las reglas y el
    # writer los ordena por impacto.
    datos_disparo: dict = {
        "documento_id": doc.id,
        "tipo_documento": doc.tipo_documento.value,
    }

    if vivienda_habitual:
        motivo = "vivienda_habitual_en_periodo"
    elif afecto_actividad:
        motivo = "afecto_actividad_economica"
    else:
        motivo = "sin_prorrateo_por_dias"
        datos_disparo["dias_a_disposicion"] = dias_a_disposicion_int
        datos_disparo["dias_no_prorrateados"] = (
            _DIAS_EJERCICIO - dias_a_disposicion_int
        )

    datos_disparo["motivo"] = motivo

    return ArgumentoCandidato(
        regla_id="R016",
        descripcion=(
            "La Administracion imputa renta inmobiliaria sobre un inmueble "
            "excluido por la norma (vivienda habitual o afecto a actividad "
            "economica) o sin prorratear la cuantia por los dias en que el "
            "inmueble estuvo efectivamente a disposicion del titular."
        ),
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo=datos_disparo,
        impacto_estimado="medio",
    )
