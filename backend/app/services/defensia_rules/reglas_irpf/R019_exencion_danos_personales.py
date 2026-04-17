"""R019 — exencion_indemnizacion_danos_personales.

Regla del Bloque II (reglas_irpf). Dispara cuando AEAT incluye como renta
sujeta una indemnizacion por danos personales que deberia estar exenta
segun el regimen de exencion tributaria de indemnizaciones por
responsabilidad civil:

    1. Cuantias legalmente reconocidas o judicialmente reconocidas.
    2. Acuerdos de mediacion y otros Metodos Alternativos de Solucion de
       Controversias (MASC), siempre dentro del limite del Baremo legal
       aplicable (extension introducida por la Ley Organica 1/2025 de
       medidas en materia de eficiencia del Servicio Publico de Justicia).
    3. Pagos realizados por aseguradoras en cumplimiento de sentencia
       firme reconociendo la indemnizacion.

Fundamento juridico (resuelto por el RAG verificador, NO hardcoded aqui):
    - Art. 7.d LIRPF: exencion de indemnizaciones como consecuencia de
      responsabilidad civil por danos personales, en la cuantia legal o
      judicialmente reconocida.
    - Ley Organica 1/2025: extension de la exencion a MASC bajo Baremo.
    - Jurisprudencia TS sobre aseguradoras y cumplimiento de sentencias.

Scope del producto (Parte 2 DefensIA):
    - Tributo: IRPF unicamente (la exencion es especifica del art. 7.d
      LIRPF y no aplica a IVA/ISD/ITP/Plusvalia Municipal).
    - Fases: todas las fases en las que el contribuyente pueda defender
      la exencion — desde la propuesta de liquidacion hasta la via TEAR.
      Se excluyen deliberadamente las fases sancionadoras (R019 ataca
      la deuda principal, no la sancion).

Invariante #2 (design Parte 2): la cita normativa devuelta por la regla
es SEMANTICA y libre. La cita canonica (`Art. 7.d LIRPF`, `LO 1/2025`,
`Baremo de la Ley 35/2015`) la resuelve el ``defensia_rag_verifier`` —
este modulo no contiene ningun literal canonico.

Decisiones de diseno (documentadas para futuros mantenedores):
    - MASC que supera el Baremo: la regla NO dispara. La parte excedente
      al limite legal no esta cubierta por la exencion y defender por
      encima seria inventarse el alcance. Es una decision conservadora
      deliberada — el writer LLM no tendra ocasion de excederse.
    - Indemnizaciones laborales pactadas: fuera de alcance de R019. El
      art. 7.e LIRPF cubre indemnizaciones por despido con su propio
      regimen (limites del ET) y su argumento defensivo corresponderia
      a otra regla distinta del rango R011-R020.
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
    "Exencion tributaria de indemnizaciones por danos personales de "
    "responsabilidad civil en cuantia legal o judicialmente reconocida, "
    "incluidos los acuerdos de mediacion y MASC dentro del limite del Baremo"
)


# Tipos de documento en los que podemos encontrar el disparo. Incluimos
# LIQUIDACION_PROVISIONAL y PROPUESTA_LIQUIDACION como canales principales
# (AEAT regulariza la exencion en estos actos), SENTENCIA_JUDICIAL cuando
# la propia resolucion reconoce la indemnizacion y OTROS para capturar
# acuerdos MASC que el clasificador no haya categorizado como categoria
# especifica.
_TIPOS_RELEVANTES = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
    TipoDocumento.SENTENCIA_JUDICIAL,
    TipoDocumento.OTROS,
)


def _evaluar_documento(datos: dict) -> tuple[str, dict] | None:
    """Evalua un unico documento y devuelve (motivo, datos_disparo) o None.

    Factorizada para que la iteracion sobre `expediente.documentos` sea
    lineal y trivial de leer. La prioridad de los triggers es:

    1. Responsabilidad civil con resolucion judicial (motivo mas solido).
    2. Aseguradora en cumplimiento de sentencia (variante del anterior).
    3. Acuerdo de mediacion / MASC dentro del Baremo (extension LO 1/2025).

    Si ninguno encaja, devuelve ``None`` y el llamador continua con el
    siguiente documento.
    """
    origen = datos.get("origen")
    incluida = bool(datos.get("incluida_como_renta_sujeta", False))
    resolucion_judicial = bool(datos.get("resolucion_judicial", False))
    en_cumplimiento_sentencia = bool(
        datos.get("en_cumplimiento_sentencia", False)
    )
    pagador = datos.get("pagador")

    # Trigger 1: responsabilidad civil con resolucion judicial y la
    # Administracion la incluye como renta sujeta.
    if (
        origen == "responsabilidad_civil_danos_personales"
        and resolucion_judicial
        and incluida
    ):
        disparo = {
            "motivo": "responsabilidad_civil_judicial",
            "origen": origen,
            "resolucion_judicial": True,
        }
        importe = datos.get("indemnizacion_declarada_exenta") or datos.get(
            "importe"
        )
        if importe is not None:
            disparo["importe"] = importe
        return ("responsabilidad_civil_judicial", disparo)

    # Trigger 2: aseguradora que paga en cumplimiento de sentencia. Aqui
    # no exigimos `origen` literal porque la fuente del pago suele venir
    # etiquetada por la aseguradora y no siempre replica el string
    # "responsabilidad_civil_danos_personales". El `en_cumplimiento_sentencia`
    # ya demuestra que existe un reconocimiento judicial previo.
    if pagador == "aseguradora" and en_cumplimiento_sentencia:
        disparo = {
            "motivo": "aseguradora_en_cumplimiento_sentencia",
            "pagador": "aseguradora",
            "en_cumplimiento_sentencia": True,
        }
        if origen:
            disparo["origen"] = origen
        importe = datos.get("importe") or datos.get(
            "indemnizacion_declarada_exenta"
        )
        if importe is not None:
            disparo["importe"] = importe
        return ("aseguradora_en_cumplimiento_sentencia", disparo)

    # Trigger 3: acuerdo de mediacion / MASC dentro del Baremo aplicable.
    # La extension LO 1/2025 acota la exencion al limite del Baremo, por
    # lo que el disparo exige explicitamente que `importe <= baremo`.
    if origen == "acuerdo_mediacion_MASC":
        importe = datos.get("importe")
        baremo = datos.get("importe_baremo_aplicable")
        if (
            importe is not None
            and baremo is not None
            and importe <= baremo
        ):
            return (
                "acuerdo_mediacion_MASC",
                {
                    "motivo": "acuerdo_mediacion_MASC",
                    "origen": origen,
                    "importe": importe,
                    "importe_baremo_aplicable": baremo,
                },
            )
        # MASC que supera el Baremo: no dispara (decision conservadora).
        return None

    return None


@regla(
    id="R019",
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
        "Inclusion como renta sujeta de indemnizacion por danos personales "
        "exenta (responsabilidad civil, cuantia legal o judicial, acuerdo "
        "MASC bajo Baremo)"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — el brief no se usa todavia pero forma parte de la firma
) -> ArgumentoCandidato | None:
    """Evalua la regla R019 sobre el expediente.

    Itera sobre los documentos relevantes (liquidacion / propuesta /
    sentencia / otros) y, al primer disparo positivo, emite un
    ``ArgumentoCandidato`` con cita semantica y ``datos_disparo``
    exponiendo el motivo. Si ningun documento encaja con alguno de los
    tres triggers, devuelve ``None``.

    El filtrado por tributo y fase lo hace el motor antes de invocar esta
    funcion — aqui solo nos ocupamos de la logica de evaluacion sobre los
    datos estructurados.
    """
    for doc in expediente.documentos:
        if doc.tipo_documento not in _TIPOS_RELEVANTES:
            continue

        datos = doc.datos or {}
        resultado = _evaluar_documento(datos)
        if resultado is None:
            continue

        _, disparo = resultado
        # Enriquecemos con trazabilidad del documento para el writer y la
        # capa de auditoria.
        disparo["documento_id"] = doc.id
        disparo["tipo_documento"] = doc.tipo_documento.value

        return ArgumentoCandidato(
            regla_id="R019",
            descripcion=(
                "La Administracion incluye como renta sujeta una "
                "indemnizacion por danos personales que se encuentra "
                "amparada por la exencion tributaria de las cuantias "
                "legal o judicialmente reconocidas (incluidos los "
                "acuerdos de mediacion y MASC dentro del limite del "
                "Baremo aplicable)."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo=disparo,
            impacto_estimado="alto",
        )

    return None
