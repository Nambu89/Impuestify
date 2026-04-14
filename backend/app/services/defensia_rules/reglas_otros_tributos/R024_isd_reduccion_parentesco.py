"""R024 — isd_reduccion_parentesco (T1B-024).

Regla del Bloque III (otros tributos — ISD). Modela el art. 20.2.a LISD
(Ley 29/1987, del Impuesto sobre Sucesiones y Donaciones) — reducciones
estatales por razon del parentesco con el causante — sin perjuicio de las
bonificaciones y mejoras aprobadas por las Comunidades Autonomas en el
marco del art. 48.1.a de la Ley 22/2009 de cesion de tributos.

Grupos de parentesco relevantes para esta regla:

    - Grupo I: descendientes y adoptados menores de 21 anos. Reduccion
      estatal ampliada por cada ano menos de 21 (con limite), ademas de
      bonificaciones autonomicas del 95-99 % en la mayoria de CCAA.
    - Grupo II: descendientes y adoptados de 21 anos o mas, conyuges,
      ascendientes y adoptantes. Reduccion estatal fija (~15.957 EUR en
      tramo estatal) y bonificacion autonomica significativa en las CCAA
      con politica bonificadora activa (Madrid, Andalucia, Cantabria,
      Canarias, La Rioja, Baleares, Galicia, Extremadura, Asturias,
      Comunidad Valenciana, Castilla-La Mancha, Castilla y Leon, Aragon,
      Cataluna con ciertas particularidades...).

Territorialmente esta primera pasada cubre el regimen comun. La extension
TS / Tribunal Supremo a no residentes UE (STS 242/2018, que permite a los
herederos no residentes UE aplicar la bonificacion autonomica de la CCAA
de residencia del causante) se resuelve por la misma via: si los datos
clasifican la bonificacion como "aplicable" pero no se ha aplicado, la
regla dispara igualmente. La cita concreta de la STS la resuelve el RAG
verificador.

La regla dispara en tres escenarios:

    1. Causahabiente de grupo I o II y la liquidacion NO aplica la
       reduccion estatal por parentesco (``reduccion_estatal_aplicada``
       es False). Error material directo.
    2. Estatal aplicada pero la bonificacion autonomica procedente de la
       CCAA del causante figura como ``bonificacion_autonomica_aplicable``
       y no se ha aplicado (``bonificacion_autonomica_aplicada`` es
       False). Error de omision, muy frecuente en complementarias.

La regla NO dispara cuando:

    - ``grupo_parentesco`` pertenece al grupo III (hermanos, sobrinos,
      tios) o IV (colaterales mas lejanos, extranos). Esta primera pasada
      cubre unicamente los grupos I y II, que son los que reciben la
      reduccion estatal maxima y la bonificacion autonomica significativa.
    - La liquidacion ya aplica tanto la reduccion estatal como la
      bonificacion autonomica procedente: no hay error material.

Invariante #2 (anti-alucinacion): la cita normativa devuelta por la
regla es SEMANTICA y libre. La cita canonica (articulo + ley + STS) la
resuelve el ``defensia_rag_verifier`` contra el corpus normativo. Por eso
aqui no aparecen literales como "Art. 20.2.a LISD", "Ley 29/1987" o
"STS 242/2018" — solo terminos semanticos descriptivos del supuesto.
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
# Constantes — grupos de parentesco cubiertos por esta primera pasada
# ---------------------------------------------------------------------------

GRUPOS_CUBIERTOS: frozenset[str] = frozenset({"I", "II"})
"""Grupos de parentesco para los que R024 evalua reducciones.

La regla se limita a los grupos I y II porque:

- Son los que reciben la reduccion estatal por parentesco en su cuantia
  maxima (art. 20.2.a LISD).
- Son los que concentran la practica totalidad de bonificaciones
  autonomicas del 95-99 % aprobadas por las CCAA en ejercicio de sus
  competencias cedidas.
- Los grupos III y IV tienen reducciones mucho mas reducidas o nulas y
  se modelaran en reglas R0xx dedicadas si el producto lo requiere.
"""


# Cita semantica libre — el RAG verificador resuelve la cita canonica.
_CITA_SEMANTICA = (
    "Reducciones estatales por razon del parentesco con el causante en los "
    "grupos I y II, sin perjuicio de las mejoras y bonificaciones "
    "autonomicas aplicables en la Comunidad Autonoma del causante"
)


# Tipos de documento en los que aparece la liquidacion / propuesta que
# contiene los datos relevantes.
_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


# ---------------------------------------------------------------------------
# Regla
# ---------------------------------------------------------------------------

@regla(
    id="R024",
    tributos=[Tributo.ISD.value],
    fases=[
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Liquidacion ISD sin aplicar reducciones por parentesco grupos I/II "
        "(estatal y bonificaciones autonomicas procedentes)"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa en esta regla
) -> ArgumentoCandidato | None:
    """Evalua la regla R024 sobre el expediente.

    Recorre los documentos del expediente buscando una liquidacion o
    propuesta que permita comprobar si se aplicaron correctamente las
    reducciones por parentesco de los grupos I y II. Si alguno de los
    disparadores coincide, devuelve el ``ArgumentoCandidato`` con impacto
    estimado ``alto`` porque el efecto recaudatorio de estas reducciones
    suele ser cuantitativamente muy relevante.

    Disparadores (por orden de especificidad):

    1. Grupo I o II y ``reduccion_estatal_aplicada`` es ``False``:
       la liquidacion ha omitido por completo la reduccion estatal por
       parentesco, lo que aumenta artificialmente la base liquidable.
    2. Grupo I o II con ``reduccion_estatal_aplicada`` ``True`` pero
       ``bonificacion_autonomica_aplicable`` ``True`` y
       ``bonificacion_autonomica_aplicada`` ``False``: la estatal esta
       bien pero se ha ignorado la bonificacion autonomica procedente.

    Si ningun disparador coincide, devuelve ``None``. El filtrado por
    tributo / fase ya lo hace el motor antes de invocar esta funcion, pero
    comprobamos aqui el tributo como defensa en profundidad por si el
    motor evolucionara en el futuro.
    """
    # Defensa en profundidad — el motor ya filtra por tributo, pero la
    # regla se declara explicitamente defensiva para que funcione igual
    # si se ejecuta desde tests unitarios que saltan el filtrado.
    if expediente.tributo != Tributo.ISD:
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

    grupo = datos.get("grupo_parentesco")
    if grupo not in GRUPOS_CUBIERTOS:
        # Grupos III y IV quedan fuera del alcance de esta primera pasada.
        return None

    reduccion_estatal_aplicada = bool(datos.get("reduccion_estatal_aplicada", False))

    # -----------------------------------------------------------------------
    # Disparador 1 — reduccion estatal por parentesco NO aplicada
    # -----------------------------------------------------------------------
    if not reduccion_estatal_aplicada:
        return ArgumentoCandidato(
            regla_id="R024",
            descripcion=(
                "La liquidacion no aplica la reduccion estatal por razon "
                "del parentesco al causahabiente del grupo "
                f"{grupo}, a pesar de que la normativa estatal reconoce "
                "una reduccion especifica para descendientes, adoptados, "
                "conyuges, ascendientes y adoptantes respecto del "
                "causante. Debe minorarse la base liquidable en la "
                "cuantia legalmente procedente."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "tipo": "reduccion_estatal_parentesco_omitida",
                "documento_id": doc_liquidacion.id,
                "tipo_documento": doc_liquidacion.tipo_documento.value,
                "grupo_parentesco": grupo,
                "reduccion_estatal_aplicada": False,
                "ccaa_causante": datos.get("ccaa_causante") or expediente.ccaa,
                "ejercicio": datos.get("ejercicio"),
            },
            impacto_estimado="alto",
        )

    # -----------------------------------------------------------------------
    # Disparador 2 — estatal OK pero bonificacion autonomica ignorada
    # -----------------------------------------------------------------------
    bonificacion_aplicable = bool(
        datos.get("bonificacion_autonomica_aplicable", False)
    )
    bonificacion_aplicada = bool(
        datos.get("bonificacion_autonomica_aplicada", False)
    )

    if bonificacion_aplicable and not bonificacion_aplicada:
        return ArgumentoCandidato(
            regla_id="R024",
            descripcion=(
                "La liquidacion aplica la reduccion estatal por parentesco "
                "pero ignora la bonificacion autonomica procedente en la "
                "Comunidad Autonoma del causante, pese a que el "
                "causahabiente pertenece al grupo "
                f"{grupo} y concurren los presupuestos para aplicarla. "
                "La competencia normativa cedida a las CCAA permite "
                "bonificaciones significativas que deben reconocerse en "
                "la cuota."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "tipo": "bonificacion_autonomica_parentesco_omitida",
                "documento_id": doc_liquidacion.id,
                "tipo_documento": doc_liquidacion.tipo_documento.value,
                "grupo_parentesco": grupo,
                "reduccion_estatal_aplicada": True,
                "bonificacion_autonomica_aplicable": True,
                "bonificacion_autonomica_aplicada": False,
                "ccaa_causante": datos.get("ccaa_causante") or expediente.ccaa,
                "ejercicio": datos.get("ejercicio"),
            },
            impacto_estimado="alto",
        )

    return None
