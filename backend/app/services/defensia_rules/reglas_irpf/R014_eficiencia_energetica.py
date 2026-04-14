"""R014 — deduccion_eficiencia_energetica (T1B-014).

Regla determinista DefensIA del grupo IRPF. Dispara cuando AEAT deniega la
deduccion por obras de mejora de eficiencia energetica en vivienda pese a que
el contribuyente haya acreditado la obra con certificado energetico valido y
dentro del periodo de vigencia.

Base normativa (para el RAG verificador — NO hardcoded aqui):
    - Disposicion Adicional Quincuagesima (DA 50.ª) LIRPF, introducida por el
      RDL 19/2021 de 5 de octubre, y prorrogada hasta 31 de diciembre de 2026.
    - Tres deducciones independientes:
        * 20 %: reduccion de al menos 7 % de la demanda de calefaccion/
          refrigeracion.
        * 40 %: reduccion de al menos 30 % del consumo de energia primaria
          no renovable, O mejora a clase energetica A o B.
        * 60 %: obras en edificios residenciales de uso predominante
          residencial que mejoren la eficiencia energetica del conjunto.

El spec original del plan citaba (erroneamente) "art. 68.7 LIRPF" — la base
correcta es la DA 50.ª. La regla emite una cita SEMANTICA libre que describe
el concepto juridico sin hardcodear ni "DA 50", ni "Disposicion Adicional
Quincuagesima", ni "RDL 19/2021", ni "art. 68.7". El RAG verificador
resuelve la cita canonica contra el corpus normativo (invariante #2 del
plan Parte 2, anti-alucinacion).

Spec: plans/2026-04-13-defensia-implementation-plan-part2.md §T1B-014
"""
from __future__ import annotations

from typing import Any, Optional

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


# ---------------------------------------------------------------------------
# Constantes y cita semantica
# ---------------------------------------------------------------------------

# Umbrales de los tres subtipos de deduccion.
_UMBRAL_REDUCCION_DEMANDA: float = 0.07
_UMBRAL_REDUCCION_CONSUMO_PRIMARIA: float = 0.30

# Clases energeticas que habilitan la deduccion del 40 % cuando se alcanzan
# como resultado de la obra. Mayusculas.
_CLASES_ENERGETICAS_HABILITANTES: frozenset[str] = frozenset({"A", "B"})

# Cita semantica — describe el concepto juridico, nunca el articulo canonico.
# Revisada explicitamente contra el test anti-hardcode de R014: NO contiene
# "DA 50", "Disposicion Adicional Quincuagesima", "RDL 19/2021" ni "art. 68.7".
_CITA_SEMANTICA = (
    "Deduccion por obras de mejora de eficiencia energetica en vivienda con "
    "certificado acreditativo de clase o reduccion de demanda/consumo, "
    "vigente para el ejercicio fiscal"
)

# Tipos de documento en los que buscamos la denegacion. Son actos
# administrativos tributarios con cuota liquidable — facturas, certificados,
# justificantes y otros medios de prueba se evaluan en sus propias reglas.
_TIPOS_LIQUIDACION: frozenset[TipoDocumento] = frozenset(
    {
        TipoDocumento.LIQUIDACION_PROVISIONAL,
        TipoDocumento.PROPUESTA_LIQUIDACION,
    }
)


# ---------------------------------------------------------------------------
# Helpers privados
# ---------------------------------------------------------------------------

def _to_float(valor: Any) -> Optional[float]:
    """Convierte un valor numerico a float de forma defensiva.

    Retorna None si el valor no es convertible (string vacio, None, objetos
    no numericos). Usado para leer umbrales de `datos` sin que una clave
    malformada tumbe la evaluacion — la regla simplemente calla.
    """
    if valor is None:
        return None
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _clase_energetica_normalizada(valor: Any) -> Optional[str]:
    """Normaliza la clase energetica a una letra mayuscula (A-G).

    Acepta strings como "a", "B ", "Clase A" (extrae la primera letra). Si no
    logra extraer una letra valida devuelve None y la regla no dispara por
    esta via.
    """
    if not isinstance(valor, str):
        return None
    limpio = valor.strip().upper()
    if not limpio:
        return None
    # Si el string es "Clase A" o similar, buscamos la primera letra A-G.
    for ch in limpio:
        if "A" <= ch <= "G":
            return ch
    return None


def _tipo_deduccion_por_datos(datos: dict) -> Optional[tuple[str, dict]]:
    """Determina que subtipo de deduccion aplica segun los `datos`.

    Retorna una tupla `(tipo, datos_disparo_parciales)`:
        - "40_por_ciento": clase A/B post-obra O reduccion consumo primaria >= 30 %.
        - "20_por_ciento": reduccion de demanda >= 7 % (y no aplica la del 40 %).
        - None: no hay evidencia de ningun subtipo.

    La deduccion del 60 % (edificios completos) NO se detecta en esta regla
    de primera pasada — requeriria datos urbanisticos adicionales y la
    cubriremos en una regla/ampliacion futura.
    """
    # Prioridad 1: clase energetica A/B post-obra habilita 40 %.
    clase = _clase_energetica_normalizada(datos.get("clase_energetica_post_obra"))
    if clase is not None and clase in _CLASES_ENERGETICAS_HABILITANTES:
        return ("40_por_ciento", {"clase_energetica": clase})

    # Prioridad 2: reduccion del consumo de energia primaria no renovable
    # igual o superior al 30 % habilita tambien el 40 %.
    consumo = _to_float(datos.get("reduccion_consumo_energia"))
    if consumo is not None and consumo >= _UMBRAL_REDUCCION_CONSUMO_PRIMARIA:
        return (
            "40_por_ciento",
            {"reduccion_consumo_energia": consumo},
        )

    # Prioridad 3: reduccion de la demanda de calefaccion/refrigeracion
    # igual o superior al 7 % habilita el 20 %.
    demanda = _to_float(datos.get("reduccion_demanda"))
    if demanda is not None and demanda >= _UMBRAL_REDUCCION_DEMANDA:
        return (
            "20_por_ciento",
            {"reduccion_demanda": demanda},
        )

    return None


def _documento_dispara(doc: DocumentoEstructurado) -> Optional[tuple[str, dict]]:
    """Evalua si un documento cumple todos los triggers para R014.

    Retorna `(tipo, datos_disparo_parciales)` si dispara, None si no.

    Requisitos acumulativos para disparar:
        1. El documento debe ser liquidacion provisional o propuesta.
        2. El contribuyente declaro la deduccion de eficiencia energetica.
        3. Presento certificado energetico (requisito formal imprescindible).
        4. AEAT no admitio la deduccion (deduccion_admitida == 0 o ausente).
        5. Se cumple al menos uno de los umbrales tecnicos (20/40/60 %).
    """
    if doc.tipo_documento not in _TIPOS_LIQUIDACION:
        return None

    datos = doc.datos or {}

    # (2) La deduccion tuvo que ser declarada.
    if datos.get("deduccion_eficiencia_declarada") is not True:
        return None

    # (3) El certificado energetico es condicion formal imprescindible. Si
    # no se aporta, la denegacion es legitima y la regla NO debe disparar
    # — este es el caso del test negativo "sin_certificado".
    if datos.get("certificado_energetico_presentado") is not True:
        return None

    # (4) Si AEAT ya admitio la deduccion (total o parcialmente) no hay
    # denegacion que impugnar — test negativo "deduccion_admitida".
    admitida = _to_float(datos.get("deduccion_admitida"))
    if admitida is not None and admitida > 0:
        return None

    # (5) Determinar subtipo tecnico.
    return _tipo_deduccion_por_datos(datos)


# ---------------------------------------------------------------------------
# Regla principal
# ---------------------------------------------------------------------------

@regla(
    id="R014",
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
        "Denegacion de deduccion por obras de mejora de eficiencia energetica "
        "en vivienda con certificado acreditativo valido"
    ),
)
def evaluar(
    expediente: ExpedienteEstructurado, brief: Brief  # noqa: ARG001 — brief no usado
) -> Optional[ArgumentoCandidato]:
    """Evalua R014 sobre el expediente.

    Recorre los documentos del expediente (timeline ordenado) y devuelve el
    primer `ArgumentoCandidato` que dispare segun `_documento_dispara`. Si
    ningun documento cumple el patron, devuelve None y la regla no se
    incluye en el dictamen.
    """
    del brief  # R014 no depende del brief del usuario — datos vienen del extractor.

    for doc in expediente.timeline_ordenado():
        disparo = _documento_dispara(doc)
        if disparo is None:
            continue

        tipo_deduccion, datos_disparo_extra = disparo

        return ArgumentoCandidato(
            regla_id="R014",
            descripcion=(
                "AEAT deniega la deduccion por obras de mejora de eficiencia "
                "energetica en vivienda pese a haber acreditado el "
                "contribuyente la obra con certificado energetico valido "
                "dentro del periodo de vigencia, cumpliendose los umbrales "
                "tecnicos que la norma exige para el subtipo declarado."
            ),
            cita_normativa_propuesta=_CITA_SEMANTICA,
            datos_disparo={
                "tipo_deduccion": tipo_deduccion,
                "documento_id": doc.id,
                "tipo_documento": doc.tipo_documento.value,
                **datos_disparo_extra,
            },
            impacto_estimado=(
                "Alegable en reposicion o TEAR: readmision de la deduccion "
                "por eficiencia energetica acreditada mediante certificado."
            ),
        )

    return None
