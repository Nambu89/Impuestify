"""R027 — plusvalia_metodo_optimo (T1B-027).

Regla del Bloque III (Plusvalia Municipal / IIVTNU). Dispara cuando el
Ayuntamiento liquida la plusvalia por el metodo objetivo con una cuota
superior a la que resultaria del metodo de estimacion directa (diferencia
entre valores de escritura de adquisicion y transmision), o cuando no se le
ofrece al contribuyente la opcion por el metodo que le resulte mas
beneficioso.

Base normativa (resuelta por el RAG verificador, no por la regla — invariante
#2):

    - Art. 107.5 TRLHL en la redaccion del RDL 26/2021, que habilita el doble
      metodo (objetivo y estimacion directa) tras la STC 182/2021 de 26 de
      octubre que declaro inconstitucional el metodo objetivo unico.
"""
from __future__ import annotations

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import regla


_CITA_SEMANTICA = (
    "Opcion del contribuyente por el metodo de determinacion de la base "
    "imponible del Impuesto sobre el Incremento del Valor de los Terrenos de "
    "Naturaleza Urbana que arroje menor cuota, entre el metodo objetivo y la "
    "estimacion directa del incremento real de valor"
)


_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
)


@regla(
    id="R027",
    tributos=[Tributo.PLUSVALIA.value],
    fases=[
        "LIQUIDACION_FIRME_PLAZO_RECURSO",
        "COMPROBACION_PROPUESTA",
        "COMPROBACION_POST_ALEGACIONES",
        "REPOSICION_INTERPUESTA",
        "TEAR_INTERPUESTA",
        "TEAR_AMPLIACION_POSIBLE",
    ],
    descripcion=(
        "Plusvalia municipal liquidada por metodo objetivo con cuota superior "
        "a la del metodo de estimacion directa tras la STC 182/2021"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001
) -> ArgumentoCandidato | None:
    """Evalua la regla R027 sobre el expediente.

    Dos disparadores:

    1. El Ayuntamiento liquida por metodo objetivo y existe una cuota de
       estimacion directa inferior: el contribuyente debio poder optar por
       la mas beneficiosa. Dispara si ``cuota_metodo_objetivo >
       cuota_metodo_directa``.
    2. El Ayuntamiento liquida por metodo objetivo y el expediente acredita
       que el incremento real es calculable (hay escrituras), pero NO se
       ofrecio la opcion por el metodo directo. Dispara si
       ``incremento_real_calculable=True`` y ``opcion_directa_ofrecida=False``.

    Si el metodo aplicado ya es "directa" o si el metodo directo arroja una
    cuota mayor o igual que el objetivo, la regla NO dispara.
    """
    if expediente.tributo != Tributo.PLUSVALIA:
        return None

    doc = next(
        (
            d
            for d in expediente.documentos
            if d.tipo_documento in _TIPOS_LIQUIDACION
        ),
        None,
    )
    if doc is None:
        return None

    datos = doc.datos or {}

    tributo_doc = datos.get("tributo")
    if isinstance(tributo_doc, str) and tributo_doc.upper() != "PLUSVALIA":
        return None

    metodo_aplicado = datos.get("metodo_aplicado")
    if isinstance(metodo_aplicado, str) and metodo_aplicado.lower() == "directa":
        return None

    cuota_objetivo = datos.get("cuota_metodo_objetivo")
    cuota_directa = datos.get("cuota_metodo_directa")

    if (
        isinstance(cuota_objetivo, (int, float))
        and isinstance(cuota_directa, (int, float))
        and cuota_objetivo > cuota_directa
    ):
        ahorro = cuota_objetivo - cuota_directa
        if isinstance(ahorro, float) and ahorro.is_integer():
            ahorro = int(ahorro)
        return ArgumentoCandidato(
            regla_id="R027",
            descripcion=(
                "La liquidacion se ha girado por el metodo objetivo con una "
                "cuota superior a la que resultaria del metodo de estimacion "
                "directa. Tras la STC 182/2021 y el RDL 26/2021, el "
                "contribuyente puede optar por el metodo que arroje menor "
                "cuota."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "tipo": "objetivo_superior_a_directa",
                "documento_id": doc.id,
                "tipo_documento": doc.tipo_documento.value,
                "cuota_metodo_objetivo": cuota_objetivo,
                "cuota_metodo_directa": cuota_directa,
                "ahorro": ahorro,
            },
            impacto_estimado="alto",
        )

    incremento_real_calculable = bool(datos.get("incremento_real_calculable", False))
    opcion_directa_ofrecida = bool(datos.get("opcion_directa_ofrecida", True))

    if (
        isinstance(cuota_objetivo, (int, float))
        and cuota_objetivo > 0
        and incremento_real_calculable
        and not opcion_directa_ofrecida
    ):
        return ArgumentoCandidato(
            regla_id="R027",
            descripcion=(
                "La Administracion local ha liquidado la plusvalia por el "
                "metodo objetivo sin ofrecer al contribuyente la opcion por "
                "el metodo de estimacion directa del incremento real de "
                "valor, pese a que los valores de escritura permitian su "
                "calculo."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "tipo": "opcion_directa_no_ofrecida",
                "documento_id": doc.id,
                "tipo_documento": doc.tipo_documento.value,
                "cuota_metodo_objetivo": cuota_objetivo,
                "incremento_real_calculable": True,
            },
            impacto_estimado="medio",
        )

    return None
