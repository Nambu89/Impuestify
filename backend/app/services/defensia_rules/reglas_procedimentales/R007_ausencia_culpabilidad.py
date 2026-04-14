"""R007 — ausencia_culpabilidad (T1B-007).

Regla del Bloque I (procedimentales). Dispara cuando el acuerdo sancionador
carece de motivacion especifica de la culpabilidad del obligado tributario:
usa formulas genericas ("resulta evidente", "el contribuyente no podia
ignorar"), razona la culpa "por exclusion" o no analiza si la norma aplicada
admite interpretacion razonable.

Fundamento juridico (resuelto por el RAG verificador, NO hardcoded aqui):
    - Art. 179.2.d LGT: exoneracion cuando el obligado haya actuado amparado
      en una interpretacion razonable de la norma.
    - Art. 183.1 LGT: las infracciones tributarias exigen dolo o culpa,
      aunque sea a titulo de simple negligencia.
    - Art. 24.2 CE: presuncion de inocencia.
    - STS 21-9-2020: la culpabilidad debe motivarse de forma especifica y
      autonoma, no basta con remitirse a la regularizacion tributaria.
    - STS 1695/2024 y linea reiterada: prohibicion de razonar la culpa "por
      exclusion" (deducir culpa porque no ve concurrencia de causa exoneratoria).

Caso David (ground truth del producto):
    La norma aplicada (art. 41 bis RIRPF sobre exencion por reinversion en
    vivienda habitual, con excepcion por separacion matrimonial ex STS
    553/2023) es objetivamente compleja. El acuerdo sancionador 191+194 que
    AEAT le notifico carece de motivacion especifica de culpabilidad. R007
    es una defensa nuclear del expediente.

Scope del producto (Parte 2 DefensIA):
    - Tributos: IRPF, IVA, ISD, ITP, Plusvalia Municipal (transversal
      sancionador).
    - Fases: SANCIONADOR_PROPUESTA, SANCIONADOR_IMPUESTA (el acuerdo ya
      esta en el expediente y permite analizar la motivacion), mas las vias
      de recurso REPOSICION_INTERPUESTA y TEAR_* (la regla sigue siendo util
      mientras la sancion no sea firme).

Invariante #2 (design Parte 2): la cita normativa devuelta por la regla es
SEMANTICA y libre. La cita canonica (articulo + ley + jurisprudencia) la
resuelve el ``defensia_rag_verifier`` contra el corpus normativo. Por eso
aqui no aparecen literales como "Art. 179.2.d LGT" ni "STS 21-9-2020" — solo
terminos semanticos ("culpabilidad", "motivacion especifica", "interpretacion
razonable").
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
    "Ausencia de motivacion especifica de la culpabilidad en el acuerdo "
    "sancionador: formulas genericas, razonamiento por exclusion o falta "
    "de analisis sobre si la norma admite interpretacion razonable"
)


# Orden de prioridad de los motivos de disparo. Si varios flags son True a la
# vez, el motivo dominante es el mas grave a efectos de defensa juridica.
# Una motivacion generica es el defecto mas visible; el razonamiento por
# exclusion es el mas proscrito por la jurisprudencia reciente; la falta de
# analisis de interpretacion razonable es el defecto estructural del acuerdo.
_TIPOS_SANCIONADOR = (
    TipoDocumento.ACUERDO_IMPOSICION_SANCION,
    TipoDocumento.PROPUESTA_SANCION,
)


@regla(
    id="R007",
    tributos=["IRPF", "IVA", "ISD", "ITP", "PLUSVALIA"],
    fases=[
        "SANCIONADOR_PROPUESTA",
        "SANCIONADOR_IMPUESTA",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    ],
    descripcion=(
        "Sancion sin motivacion especifica de culpabilidad (principios de "
        "culpabilidad y presuncion de inocencia en el ordenamiento sancionador "
        "tributario)"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R007 sobre el expediente.

    La funcion busca un documento sancionador (``ACUERDO_IMPOSICION_SANCION``
    o, subsidiariamente, ``PROPUESTA_SANCION``) y comprueba tres flags en
    ``datos``:

    - ``motivacion_culpabilidad_generica``: el acuerdo usa formulas genericas
      tipo "resulta evidente" o "el contribuyente no podia ignorar".
    - ``razonamiento_por_exclusion``: el acuerdo deduce la culpa solo porque
      no ve concurrencia de alguna causa de exoneracion, sin probar dolo o
      culpa positiva.
    - ``analisis_interpretacion_razonable``: si es ``False`` o esta ausente,
      el acuerdo no analiza si la norma aplicada admite interpretacion
      razonable ex art. 179.2.d LGT.

    Si al menos uno de los tres defectos de motivacion esta presente, la regla
    devuelve un ``ArgumentoCandidato``. En caso contrario (o si no hay
    documento sancionador en el expediente) devuelve ``None``.

    El filtrado por fase lo hace el motor antes de invocar esta funcion, pero
    como defensa en profundidad la regla comprueba igualmente que al menos un
    documento sea de tipo sancionador — esto evita falsos positivos en
    expedientes donde la fase este mal clasificada.
    """
    doc_sancion = next(
        (d for d in expediente.documentos if d.tipo_documento in _TIPOS_SANCIONADOR),
        None,
    )
    if doc_sancion is None:
        # No hay documento sancionador en el expediente — nada que motivar.
        return None

    datos = doc_sancion.datos or {}
    motivacion_generica = bool(datos.get("motivacion_culpabilidad_generica", False))
    razonamiento_exclusion = bool(datos.get("razonamiento_por_exclusion", False))
    # Por diseno: si la flag no esta presente asumimos que el acuerdo NO
    # analiza la interpretacion razonable (carga de prueba para AEAT). Solo
    # un ``True`` explicito exime a la regla de disparar por este motivo.
    analiza_interpretacion = bool(datos.get("analisis_interpretacion_razonable", False))

    if not (motivacion_generica or razonamiento_exclusion or not analiza_interpretacion):
        return None

    # Prioridad del motivo dominante para el campo `datos_disparo.motivo`.
    # Usamos un orden estable que facilita la lectura del argumento en el
    # escrito posterior y permite tests deterministas.
    if motivacion_generica:
        motivo = "motivacion_generica"
    elif razonamiento_exclusion:
        motivo = "razonamiento_por_exclusion"
    else:
        motivo = "sin_analisis_interpretacion_razonable"

    return ArgumentoCandidato(
        regla_id="R007",
        descripcion=(
            "El acuerdo sancionador no motiva de forma especifica la "
            "culpabilidad del obligado tributario: emplea formulas genericas, "
            "razona la culpa por exclusion o no analiza si la norma aplicada "
            "admite interpretacion razonable. La carga de motivar la "
            "culpabilidad corresponde a la Administracion y no puede "
            "deducirse automaticamente de la regularizacion tributaria."
        ),
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo={
            "motivo": motivo,
            "documento_id": doc_sancion.id,
            "tipo_documento": doc_sancion.tipo_documento.value,
            "motivacion_culpabilidad_generica": motivacion_generica,
            "razonamiento_por_exclusion": razonamiento_exclusion,
            "analisis_interpretacion_razonable": analiza_interpretacion,
        },
        impacto_estimado="alto",
    )
