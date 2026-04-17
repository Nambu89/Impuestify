"""R021 — iva_prorrata (T1B-021).

Regla del Bloque III (otros tributos, bloque IVA). Modela el regimen de
prorrata del Impuesto sobre el Valor Anadido conforme a los arts. 102 a 106
LIVA. La regla general es la prorrata general, pero el art. 106 LIVA obliga
a aplicar la prorrata especial cuando la deduccion que resultaria de aplicar
la general exceda en un 10 % o mas a la que se obtendria con la especial.

El Tribunal Supremo ha calificado la eleccion entre prorrata general y
especial como una opcion tributaria en sentido propio, por lo que su
denegacion requiere una motivacion material que analice si concurrian los
supuestos de obligatoriedad del art. 106 LIVA.

La regla dispara cuando la AEAT:

    - Aplica la prorrata general pese a que la deduccion resultante excedia
      en mas del 10 % a la que habria correspondido con la prorrata especial
      (especial obligatoria no reconocida).
    - Deniega al sujeto pasivo su opcion por la prorrata especial sin
      analizar previamente si concurria el supuesto de obligatoriedad.

La regla NO dispara cuando:

    - La diferencia entre deduccion general y especial es inferior al 10 %:
      la general es valida y no procede la especial obligatoria.
    - El sujeto pasivo ya tiene aplicada la prorrata especial (no hay
      conflicto vivo que defender).
    - El tributo del expediente no es IVA (el motor filtra antes, pero se
      deja una guarda adicional por defensa en profundidad).

Invariante #2 (anti-alucinacion): la cita normativa devuelta por la regla es
SEMANTICA y libre. La cita canonica (arts. 102 a 106 LIVA) la resuelve el
``defensia_rag_verifier`` contra el corpus normativo. Por eso aqui no
aparecen literales como "Art. 102 LIVA" ni "art. 106 LIVA" — solo terminos
semanticos descriptivos del supuesto.
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


# ---------------------------------------------------------------------------
# Constantes — umbrales del regimen de prorrata del IVA (arts. 102-106 LIVA)
# ---------------------------------------------------------------------------

UMBRAL_OBLIGATORIEDAD_ESPECIAL = 0.10
"""Umbral que activa la obligatoriedad de la prorrata especial (porcentaje).

Si la deduccion que resulta de aplicar la prorrata general excede en un 10 %
o mas a la que se obtendria con la prorrata especial, la especial deja de
ser una opcion y pasa a ser obligatoria. Es un umbral relativo, no absoluto.
"""


# Cita semantica libre — el RAG verificador resuelve la cita canonica.
_CITA_SEMANTICA = (
    "Aplicacion erronea del regimen de prorrata en el Impuesto sobre el "
    "Valor Anadido, especial obligatoria frente a general cuando la "
    "deduccion resultante difiere en mas del diez por ciento"
)


# Tipos de documento donde puede aparecer una liquidacion con prorrata mal
# aplicada. Se mira tanto la liquidacion provisional como la propuesta — el
# conflicto puede instanciarse en cualquiera de las dos fases.
_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


# ---------------------------------------------------------------------------
# Regla
# ---------------------------------------------------------------------------

@regla(
    id="R021",
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
        "Prorrata IVA aplicada erroneamente — especial obligatoria no "
        "reconocida por AEAT o denegacion de la opcion sin analisis de "
        "obligatoriedad"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa aun pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R021 sobre el expediente.

    Se recorren los documentos del expediente buscando dos disparadores en
    orden de especificidad:

    1. Liquidacion/propuesta con ``prorrata_general_aplicada`` y con una
       diferencia superior al umbral entre la deduccion general y la
       especial: la especial era obligatoria por mandato del art. 106 LIVA
       y no se ha reconocido. Se exige explicitamente que la especial NO
       este ya aplicada (``prorrata_especial_aplicada != True``).
    2. Liquidacion/propuesta donde el sujeto pasivo solicito la prorrata
       especial, fue denegada, y no consta analisis de obligatoriedad: la
       denegacion carece de la motivacion material que exige la calificacion
       de la eleccion como opcion tributaria.

    Si ninguno dispara, devuelve ``None``. El filtrado por tributo/fase ya
    lo hace el motor antes de invocar esta funcion, pero se mantiene una
    guarda adicional sobre ``expediente.tributo`` por defensa en profundidad.
    """
    # Defensa en profundidad — el motor ya filtra por tributo, pero si algun
    # caller invoca directamente a la regla fuera del motor nos aseguramos
    # de no disparar sobre expedientes que no son de IVA.
    if expediente.tributo != Tributo.IVA:
        return None

    doc_liquidacion = next(
        (
            d
            for d in expediente.documentos
            if d.tipo_documento in _TIPOS_LIQUIDACION
        ),
        None,
    )
    if doc_liquidacion is None:
        return None

    datos = doc_liquidacion.datos or {}

    # Si la propia liquidacion declara un tributo distinto de IVA pese a que
    # el expediente lo marca como IVA, nos abstenemos — no queremos disparar
    # sobre un documento incongruente.
    tributo_doc = datos.get("tributo")
    if isinstance(tributo_doc, str) and tributo_doc.upper() != "IVA":
        return None

    # -----------------------------------------------------------------------
    # Disparador 1 — especial obligatoria no aplicada (diferencia > 10 %)
    # -----------------------------------------------------------------------
    prorrata_general = bool(datos.get("prorrata_general_aplicada", False))
    prorrata_especial_aplicada = bool(datos.get("prorrata_especial_aplicada", False))
    deduccion_general = datos.get("deduccion_general")
    deduccion_especial = datos.get("deduccion_especial")

    if (
        prorrata_general
        and not prorrata_especial_aplicada
        and isinstance(deduccion_general, (int, float))
        and isinstance(deduccion_especial, (int, float))
        and deduccion_especial > 0
    ):
        # Diferencia relativa = (general - especial) / especial. Si excede el
        # 10 % la prorrata especial es obligatoria por mandato del art. 106
        # LIVA. Usamos diferencia relativa sobre la especial porque el
        # supuesto legal se expresa como "la deduccion general excede en un
        # X % a la especial".
        diferencia_relativa = (deduccion_general - deduccion_especial) / deduccion_especial
        if diferencia_relativa > UMBRAL_OBLIGATORIEDAD_ESPECIAL:
            return ArgumentoCandidato(
                regla_id="R021",
                descripcion=(
                    "La Administracion ha aplicado la prorrata general del "
                    "IVA pese a que la deduccion resultante excedia en mas "
                    "del diez por ciento a la que habria correspondido con "
                    "la prorrata especial, supuesto en el que la especial "
                    "deja de ser optativa y pasa a ser obligatoria."
                ),
                cita_normativa_propuesta=_CITA_SEMANTICA,
                datos_disparo={
                    "tipo": "especial_obligatoria_no_aplicada",
                    "documento_id": doc_liquidacion.id,
                    "tipo_documento": doc_liquidacion.tipo_documento.value,
                    "deduccion_general": deduccion_general,
                    "deduccion_especial": deduccion_especial,
                    "diferencia_relativa": diferencia_relativa,
                    "umbral_obligatoriedad": UMBRAL_OBLIGATORIEDAD_ESPECIAL,
                    "ejercicio": datos.get("ejercicio"),
                },
                impacto_estimado="alto",
            )

    # -----------------------------------------------------------------------
    # Disparador 2 — opcion especial denegada sin analisis de obligatoriedad
    # -----------------------------------------------------------------------
    especial_solicitada = bool(datos.get("especial_solicitada", False))
    especial_denegada = bool(datos.get("especial_denegada", False))
    # `analisis_obligatoriedad` se interpreta como "la AEAT ha razonado si
    # concurrian los supuestos de obligatoriedad del art. 106 LIVA". Default
    # implicito: False — exigimos un flag explicito True para considerar
    # motivada la denegacion.
    analisis_obligatoriedad = bool(datos.get("analisis_obligatoriedad", False))

    if (
        especial_solicitada
        and especial_denegada
        and not analisis_obligatoriedad
        and not prorrata_especial_aplicada
    ):
        return ArgumentoCandidato(
            regla_id="R021",
            descripcion=(
                "La Administracion deniega la opcion del sujeto pasivo por "
                "la prorrata especial del IVA sin analizar si concurrian "
                "los supuestos que la hacen obligatoria, lo que priva a la "
                "resolucion de la motivacion material exigida a toda "
                "decision sobre opciones tributarias."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "tipo": "opcion_especial_denegada_sin_analisis",
                "documento_id": doc_liquidacion.id,
                "tipo_documento": doc_liquidacion.tipo_documento.value,
                "especial_solicitada": especial_solicitada,
                "especial_denegada": especial_denegada,
                "analisis_obligatoriedad": analisis_obligatoriedad,
                "ejercicio": datos.get("ejercicio"),
            },
            impacto_estimado="medio",
        )

    return None
