"""Clasificación rápida de documentos tributarios por patrones textuales.

Este módulo realiza la clasificación determinista (sin LLM) de un documento
tributario a partir de su texto extraído. Se usa como fast-path antes de
Gemini Vision y como verificación cruzada de la salida de este.

Orden de evaluación: los patrones más específicos primero para evitar falsos
positivos con patrones genéricos (ej: "ACUERDO DE IMPOSICIÓN DE SANCIÓN"
debe matchear antes que "PROPUESTA DE SANCIÓN" porque ambos contienen
"sanción").
"""
from __future__ import annotations
import re
from app.models.defensia import TipoDocumento


_PATRONES: list[tuple[TipoDocumento, list[re.Pattern]]] = [
    (TipoDocumento.LIQUIDACION_PROVISIONAL, [
        re.compile(r"notificaci[óo]n\s+de\s+resoluci[óo]n\s+con\s+liquidaci[óo]n\s+provisional", re.I),
        re.compile(r"^liquidaci[óo]n\s+provisional", re.I | re.M),
    ]),
    (TipoDocumento.PROPUESTA_LIQUIDACION, [
        re.compile(r"propuesta\s+de\s+liquidaci[óo]n", re.I),
    ]),
    (TipoDocumento.ACUERDO_IMPOSICION_SANCION, [
        re.compile(r"acuerdo\s+de\s+imposici[óo]n\s+de\s+sanci[óo]n", re.I),
    ]),
    (TipoDocumento.PROPUESTA_SANCION, [
        re.compile(r"propuesta\s+de\s+(resoluci[óo]n\s+de\s+)?sanci[óo]n", re.I),
    ]),
    (TipoDocumento.ACUERDO_INICIO_SANCIONADOR, [
        re.compile(r"acuerdo\s+de\s+inicio\s+de\s+expediente\s+sancionador", re.I),
        re.compile(r"inicio\s+de\s+expediente\s+sancionador", re.I),
    ]),
    (TipoDocumento.REQUERIMIENTO, [
        re.compile(r"^\s*requerimiento\b", re.I | re.M),
        re.compile(r"en\s+uso\s+de\s+las\s+facultades\s+que\s+confiere", re.I),
    ]),
    (TipoDocumento.ESCRITO_RECLAMACION_TEAR_USUARIO, [
        re.compile(r"al\s+tribunal\s+econ[óo]mico[\s\-]administrativo\s+regional", re.I),
        re.compile(r"interpone\s+reclamaci[óo]n\s+econ[óo]mico[\s\-]administrativa", re.I),
    ]),
    (TipoDocumento.ESCRITO_REPOSICION_USUARIO, [
        re.compile(r"interpone\s+recurso\s+de\s+reposici[óo]n", re.I),
    ]),
    (TipoDocumento.ESCRITO_ALEGACIONES_USUARIO, [
        re.compile(r"presenta\s+alegaciones", re.I),
        re.compile(r"escrito\s+de\s+alegaciones", re.I),
    ]),
    (TipoDocumento.ACTA_INSPECCION, [
        re.compile(r"acta\s+de\s+(conformidad|disconformidad|con\s+acuerdo)", re.I),
        re.compile(r"\bA\d{2}-\d", re.I),
    ]),
    (TipoDocumento.PROVIDENCIA_APREMIO, [
        re.compile(r"providencia\s+de\s+apremio", re.I),
    ]),
    (TipoDocumento.RESOLUCION_TEAR, [
        re.compile(r"resoluci[óo]n\s+del\s+tribunal\s+econ[óo]mico", re.I),
    ]),
    (TipoDocumento.RESOLUCION_TEAC, [
        re.compile(r"resoluci[óo]n\s+del\s+tribunal\s+econ[óo]mico[\s\-]administrativo\s+central", re.I),
    ]),
    (TipoDocumento.SENTENCIA_JUDICIAL, [
        re.compile(r"sentencia\s+n[º°]?\s*\d+", re.I),
    ]),
    (TipoDocumento.JUSTIFICANTE_PAGO, [
        re.compile(r"justificante\s+de\s+(pago|ingreso|presentaci[óo]n)", re.I),
    ]),
    (TipoDocumento.FACTURA, [
        re.compile(r"^\s*factura\b", re.I | re.M),
    ]),
    (TipoDocumento.ESCRITURA, [
        re.compile(r"escritura\s+de\s+(compraventa|donaci[óo]n|herencia)", re.I),
    ]),
    (TipoDocumento.LIBRO_REGISTRO, [
        re.compile(r"libro\s+registro", re.I),
    ]),
]


def clasificar_por_texto(texto: str) -> TipoDocumento:
    """Clasifica un documento según patrones textuales conocidos.

    Devuelve TipoDocumento.OTROS si ningún patrón coincide.
    """
    for tipo, patrones in _PATRONES:
        for patron in patrones:
            if patron.search(texto):
                return tipo
    return TipoDocumento.OTROS
