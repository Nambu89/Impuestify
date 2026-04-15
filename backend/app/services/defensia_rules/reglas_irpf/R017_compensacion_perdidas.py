"""R017 — compensacion_perdidas_patrimoniales_4_anos (T1B-017).

Regla del Bloque II (IRPF sustantivas). Dispara cuando el contribuyente tiene
perdidas patrimoniales declaradas en ejercicios anteriores pendientes de
compensar DENTRO del plazo de cuatro ejercicios siguientes, y la liquidacion
practicada por la Administracion NO las aplica (o las aplica por debajo del
limite normativo) contra el saldo positivo de ganancias/rendimientos del
ejercicio en cuestion.

Fundamento juridico (resuelto por el RAG verificador, NO hardcoded aqui):
    - Art. 49 LIRPF: integracion y compensacion de rentas en la base imponible
      del ahorro. Saldo negativo de perdidas patrimoniales compensable en los
      cuatro ejercicios siguientes con el limite del 25% del saldo positivo
      de los rendimientos del capital mobiliario.
    - Art. 48 LIRPF: integracion y compensacion de rentas en la base imponible
      general (perdidas no derivadas de transmisiones).

Scope del producto (Parte 2 DefensIA):
    - Tributos: exclusivamente IRPF (la compensacion de perdidas es una
      institucion propia del impuesto sobre la renta, no aplica a IVA/ISD/ITP/
      Plusvalia).
    - Fases: todas las fases en las que la liquidacion es aun impugnable:
      COMPROBACION_PROPUESTA, COMPROBACION_POST_ALEGACIONES,
      LIQUIDACION_FIRME_PLAZO_RECURSO, REPOSICION_INTERPUESTA,
      TEAR_INTERPUESTA, TEAR_AMPLIACION_POSIBLE.

Relevancia caso David Oliva: condicional. Si David tiene perdidas patrimoniales
pendientes de los ejercicios 2020-2023 y AEAT deniega la exencion por
reinversion de vivienda 2024, la ganancia resultante debe compensarse con
esas perdidas antes de calcular la cuota impugnada. La regla no depende del
caso David — se dispara cada vez que el extractor encuentra perdidas
pendientes no aplicadas en la liquidacion del ejercicio actual.

Invariante #2 (design Parte 2): la cita normativa devuelta por la regla
es SEMANTICA. La cita canonica ("Art. 49 LIRPF", parrafos, apartados) la
resuelve el ``defensia_rag_verifier`` contra el corpus normativo.
"""
from __future__ import annotations

from typing import Any

from app.models.defensia import (
    ArgumentoCandidato,
    Brief,
    ExpedienteEstructurado,
    Fase,
    TipoDocumento,
    Tributo,
)
from app.services.defensia_rules_engine import regla


# Cita semantica libre — el RAG verificador resuelve la referencia canonica.
# Nunca debe contener "Art. 49", "LIRPF" ni numeros de articulo.
_CITA_SEMANTICA = (
    "Compensacion de saldos negativos de perdidas patrimoniales pendientes "
    "de ejercicios anteriores, dentro del plazo de cuatro anos, contra las "
    "ganancias patrimoniales del ejercicio actual"
)

# Plazo normativo de arrastre de perdidas patrimoniales (ejercicios).
_PLAZO_EJERCICIOS = 4

# Tipos de documento que pueden aportar los datos de compensacion. La
# liquidacion/propuesta es la fuente primaria porque es donde AEAT calcula
# (o deja de calcular) la compensacion; OTROS se admite como ultimo recurso
# cuando el extractor deposita los datos en un documento auxiliar.
_TIPOS_LIQUIDACION = (
    TipoDocumento.LIQUIDACION_PROVISIONAL,
    TipoDocumento.PROPUESTA_LIQUIDACION,
    TipoDocumento.OTROS,
)


def _total_pendiente_en_plazo(
    perdidas_pendientes: list[dict[str, Any]],
    ejercicio_actual: int,
) -> int:
    """Suma las perdidas pendientes que todavia estan dentro del plazo.

    Una perdida del ejercicio E puede compensarse en los 4 ejercicios
    siguientes (E+1, E+2, E+3, E+4). Si ``ejercicio_actual - E > 4`` la
    perdida ha caducado y no se cuenta para el disparo de la regla.
    """
    total = 0
    for item in perdidas_pendientes or []:
        try:
            ejercicio = int(item.get("ejercicio"))
            importe = item.get("importe", 0) or 0
        except (TypeError, ValueError):
            continue
        if ejercicio_actual - ejercicio > _PLAZO_EJERCICIOS:
            continue  # caducada: fuera del plazo de 4 anos
        if ejercicio > ejercicio_actual:
            continue  # ejercicio futuro — dato incoherente, ignorar
        total += float(importe)
    # Devolvemos int cuando no hay decimales para mantener la forma limpia del
    # dato en datos_disparo (los tests comparan con enteros).
    return int(total) if float(total).is_integer() else total  # type: ignore[return-value]


@regla(
    id="R017",
    tributos=[Tributo.IRPF.value],
    fases=[
        Fase.LIQUIDACION_FIRME_PLAZO_RECURSO.value,
        Fase.COMPROBACION_PROPUESTA.value,
        Fase.COMPROBACION_POST_ALEGACIONES.value,
        Fase.REPOSICION_INTERPUESTA.value,
        Fase.TEAR_INTERPUESTA.value,
        Fase.TEAR_AMPLIACION_POSIBLE.value,
    ],
    descripcion=(
        "Compensacion no aplicada de perdidas patrimoniales pendientes de "
        "ejercicios anteriores dentro del plazo de cuatro anos"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado,
    brief: Brief,  # noqa: ARG001 — firma estandar del motor
) -> ArgumentoCandidato | None:
    """Evalua la regla R017 sobre el expediente.

    Busca el primer documento de tipo liquidacion (o documento auxiliar con
    los datos de compensacion) y evalua:

    1. Existen perdidas pendientes ``perdidas_pendientes_ejercicios_anteriores``.
    2. Al menos una esta dentro del plazo de ``_PLAZO_EJERCICIOS`` ejercicios.
    3. ``perdidas_compensadas_ejercicio_actual`` es inferior a:
        - El ``limite_compensacion_calculado`` si existe (limite del 25% del
          saldo positivo calculado aguas arriba por el extractor).
        - O al total de perdidas pendientes en plazo si el limite no esta
          disponible (fallback conservador: cualquier compensacion por debajo
          del total pendiente dispara la regla).

    Devuelve ``None`` cuando no hay documento valido, no hay perdidas dentro
    del plazo, o la compensacion ya alcanza el limite.
    """
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

    # Ejercicio actual: usamos el declarado por el extractor; si no llega,
    # no podemos determinar el plazo de arrastre y salimos sin disparar.
    try:
        ejercicio_actual = int(datos.get("ejercicio"))
    except (TypeError, ValueError):
        return None

    perdidas_pendientes = datos.get("perdidas_pendientes_ejercicios_anteriores") or []
    if not isinstance(perdidas_pendientes, list) or not perdidas_pendientes:
        return None

    total_pendiente = _total_pendiente_en_plazo(
        perdidas_pendientes, ejercicio_actual
    )
    if total_pendiente <= 0:
        # Todas las perdidas han caducado o el total es nulo.
        return None

    compensado_actual = float(datos.get("perdidas_compensadas_ejercicio_actual") or 0)

    # Limite normativo: si el extractor lo ha calculado ya, lo usamos. En
    # caso contrario caemos al total pendiente (peor caso para el contribuyente:
    # exigir compensacion completa no tiene sentido si el 25% es menor, pero
    # al menos dispara la revision humana).
    limite_declarado = datos.get("limite_compensacion_calculado")
    if limite_declarado is None:
        limite_aplicable: float = float(total_pendiente)
    else:
        try:
            limite_aplicable = float(limite_declarado)
        except (TypeError, ValueError):
            limite_aplicable = float(total_pendiente)

    # Si AEAT ya ha compensado al maximo permitido, la regla no tiene nada
    # que reclamar.
    if compensado_actual >= limite_aplicable:
        return None

    delta = limite_aplicable - compensado_actual
    # Normalizamos a int cuando no hay decimales para mantener limpios los
    # datos_disparo que los tests comparan con enteros.
    delta_norm: Any = int(delta) if float(delta).is_integer() else delta
    compensado_norm: Any = (
        int(compensado_actual)
        if float(compensado_actual).is_integer()
        else compensado_actual
    )
    limite_norm: Any = (
        int(limite_aplicable)
        if float(limite_aplicable).is_integer()
        else limite_aplicable
    )

    return ArgumentoCandidato(
        regla_id="R017",
        descripcion=(
            "La liquidacion no aplica (o aplica por debajo del limite legal) "
            "la compensacion de perdidas patrimoniales pendientes declaradas "
            "en ejercicios anteriores dentro del plazo de cuatro anos."
        ),
        cita_normativa_propuesta=_CITA_SEMANTICA,
        datos_disparo={
            "ejercicio_actual": ejercicio_actual,
            "perdidas_pendientes_total": total_pendiente,
            "compensado_actual": compensado_norm,
            "limite_aplicable": limite_norm,
            "delta_no_aplicado": delta_norm,
            "documento_id": doc_liquidacion.id,
            "tipo_documento": doc_liquidacion.tipo_documento.value,
        },
        impacto_estimado="alto",
    )
