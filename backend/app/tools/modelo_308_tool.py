"""
Modelo 308 (Solicitud de Devolucion — Sujetos Ocasionales y RE Tax-free)
Tool for TaxIA.

Per Orden EHA/3786/2008 (Art. 7) and modificaciones posteriores
(Orden HAP/2215/2013), the Modelo 308 is a *refund request* limited to three
exhaustive supuestos:

1. **Sujetos pasivos ocasionales** que entregan medios de transporte nuevos
   en operaciones intracomunitarias exentas (Art. 25.uno y dos LIVA). Solicitan
   la devolucion del IVA soportado al adquirir ese medio de transporte.
   Plazo: 30 dias naturales desde la fecha de la entrega.

2. **Sujetos pasivos en regimen simplificado de IVA** dedicados al transporte
   de viajeros o de mercancias por carretera, que adquieren vehiculos afectos
   a la actividad. Solicitan la devolucion del IVA soportado deducible.
   Plazo: 20 primeros dias naturales del mes siguiente al de la adquisicion.

3. **Comerciantes minoristas en Recargo de Equivalencia** que han devuelto IVA
   a viajeros extracomunitarios en el regimen tax-free (Art. 21.2 LIVA).
   Solicitan el reembolso de las cantidades devueltas a esos viajeros.
   Plazo: 20 primeros dias naturales del mes siguiente al trimestre, o
   30 de enero para el 4T.

NO confundir con el Modelo 309 (autoliquidacion no periodica), que es el
modelo correcto cuando un comerciante en RE realiza adquisiciones
intracomunitarias, importaciones o ISP.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# Casos legitimos del Modelo 308 (Art. 7 Orden EHA/3786/2008)
CASOS_VALIDOS = {
    "transporte_ocasional",  # Sujeto ocasional — medio de transporte nuevo
    "transportista_simplificado",  # Transportista en regimen simplificado
    "re_viajeros",  # RE — devoluciones a viajeros (tax-free)
}

MODELO_308_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_308",
        "description": """USAR ESTA FUNCION SOLO en estos tres supuestos
exhaustivos de la Orden EHA/3786/2008 Art. 7:

1. Particular o sujeto ocasional que vende un medio de transporte nuevo
   (vehiculo, embarcacion o aeronave) a otro Estado miembro de la UE y quiere
   recuperar el IVA que pago al comprarlo. (caso='transporte_ocasional')

2. Transportista autonomo en regimen simplificado de IVA (transporte de
   viajeros o mercancias por carretera) que adquiere un vehiculo afecto a la
   actividad y quiere la devolucion del IVA soportado deducible.
   (caso='transportista_simplificado')

3. Comercio minorista (farmacia, tienda, etc.) en regimen de Recargo de
   Equivalencia que ha devuelto IVA a turistas extracomunitarios en el
   regimen tax-free (Art. 21.2 LIVA), y solicita el reembolso de lo devuelto.
   (caso='re_viajeros')

NO usar para adquisiciones intracomunitarias, importaciones o inversion del
sujeto pasivo de un comerciante en RE — eso es Modelo 309, no 308.
""",
        "parameters": {
            "type": "object",
            "properties": {
                "caso": {
                    "type": "string",
                    "enum": [
                        "transporte_ocasional",
                        "transportista_simplificado",
                        "re_viajeros",
                    ],
                    "description": (
                        "Supuesto del Art. 7 Orden EHA/3786/2008. "
                        "'transporte_ocasional' = sujeto ocasional medio "
                        "de transporte nuevo. 'transportista_simplificado' = "
                        "transportista en regimen simplificado adquiriendo "
                        "vehiculo. 're_viajeros' = comerciante en RE que "
                        "reembolsa devolucion IVA a viajeros (tax-free)."
                    ),
                },
                "iva_soportado_transporte_nuevo": {
                    "type": "number",
                    "description": "Caso 'transporte_ocasional': IVA soportado al adquirir el medio de transporte nuevo que ahora se entrega intracomunitariamente. Por defecto: 0",
                },
                "fecha_entrega_transporte": {
                    "type": "string",
                    "description": "Caso 'transporte_ocasional': fecha (YYYY-MM-DD) de la entrega intracomunitaria del medio de transporte. Sirve para calcular el plazo (30 dias desde la entrega).",
                },
                "iva_soportado_vehiculo_simplificado": {
                    "type": "number",
                    "description": "Caso 'transportista_simplificado': IVA soportado deducible en la adquisicion del vehiculo afecto. Por defecto: 0",
                },
                "fecha_adquisicion_vehiculo": {
                    "type": "string",
                    "description": "Caso 'transportista_simplificado': fecha (YYYY-MM-DD) de la adquisicion del vehiculo. Sirve para calcular el plazo (20 dias del mes siguiente).",
                },
                "iva_devuelto_a_viajeros": {
                    "type": "number",
                    "description": "Caso 're_viajeros': total de IVA reembolsado por el comerciante en RE a viajeros extracomunitarios en el trimestre. Por defecto: 0",
                },
                "periodo": {
                    "type": "string",
                    "description": "Caso 're_viajeros': trimestre del reembolso ('1T', '2T', '3T' o '4T').",
                },
                "year": {
                    "type": "integer",
                    "description": "Ano fiscal. Por defecto: ano actual",
                },
            },
            "required": ["caso"],
        },
    },
}


def _calc_plazo_transporte_ocasional(fecha_entrega: str | None) -> str:
    """Plazo: 30 dias naturales desde la fecha de entrega."""
    if not fecha_entrega:
        return "30 dias naturales desde la fecha de entrega del medio de transporte."
    try:
        f = datetime.strptime(fecha_entrega, "%Y-%m-%d").date()
        from datetime import timedelta

        deadline = f + timedelta(days=30)
        return f"hasta el {deadline.strftime('%d/%m/%Y')} (30 dias naturales desde la entrega)."
    except ValueError:
        return "30 dias naturales desde la fecha de entrega del medio de transporte."


def _calc_plazo_transportista(fecha_adq: str | None) -> str:
    """Plazo: 20 primeros dias naturales del mes siguiente al de la adquisicion."""
    if not fecha_adq:
        return "20 primeros dias naturales del mes siguiente al de la " "adquisicion del vehiculo."
    try:
        f = datetime.strptime(fecha_adq, "%Y-%m-%d").date()
        # Primer dia del mes siguiente
        if f.month == 12:
            year_next = f.year + 1
            month_next = 1
        else:
            year_next = f.year
            month_next = f.month + 1
        from datetime import date

        deadline = date(year_next, month_next, 20)
        return f"hasta el {deadline.strftime('%d/%m/%Y')} (20 primeros dias del mes siguiente)."
    except ValueError:
        return "20 primeros dias naturales del mes siguiente al de la " "adquisicion del vehiculo."


def _plazo_re_viajeros(periodo: str) -> str:
    plazos = {
        "1T": "20 de abril",
        "2T": "20 de julio",
        "3T": "20 de octubre",
        "4T": "30 de enero (del ano siguiente)",
    }
    return f"hasta el {plazos.get(periodo, '20 dias del mes siguiente al trimestre')}."


async def calculate_modelo_308_tool(
    caso: str,
    iva_soportado_transporte_nuevo: float = 0,
    fecha_entrega_transporte: str | None = None,
    iva_soportado_vehiculo_simplificado: float = 0,
    fecha_adquisicion_vehiculo: str | None = None,
    iva_devuelto_a_viajeros: float = 0,
    periodo: str | None = None,
    year: int = None,
    restricted_mode: bool = False,
) -> dict[str, Any]:
    """
    Calculate the Modelo 308 refund for one of the three legitimate cases
    of Art. 7 Orden EHA/3786/2008.
    """
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response

        logger.warning("calculate_modelo_308 called in restricted_mode — blocking")
        return {
            "success": False,
            "error": "restricted",
            "formatted_response": get_autonomo_block_response(),
        }

    try:
        if year is None:
            year = datetime.now().year

        caso_norm = (caso or "").strip().lower()
        if caso_norm not in CASOS_VALIDOS:
            return {
                "success": False,
                "error": (
                    f"Caso invalido: '{caso}'. Debe ser uno de: " f"{sorted(CASOS_VALIDOS)}."
                ),
                "formatted_response": (
                    "El Modelo 308 solo cubre tres supuestos: sujeto ocasional "
                    "por entrega de medio de transporte nuevo, transportista en "
                    "regimen simplificado adquiriendo vehiculo, o comerciante en "
                    "Recargo de Equivalencia que reembolsa IVA a viajeros "
                    "(tax-free). Si el supuesto es otro (adquisicion "
                    "intracomunitaria de un comerciante en RE, ISP, importacion), "
                    "el modelo correcto es el 309."
                ),
            }

        # ===== CASO 1: SUJETO OCASIONAL — MEDIO DE TRANSPORTE NUEVO =====
        if caso_norm == "transporte_ocasional":
            if iva_soportado_transporte_nuevo < 0:
                return {
                    "success": False,
                    "error": "iva_soportado_transporte_nuevo no puede ser negativo",
                    "formatted_response": (
                        "El IVA soportado en el medio de transporte no puede " "ser negativo."
                    ),
                }
            cuota_devolver = round(iva_soportado_transporte_nuevo, 2)
            plazo_label = _calc_plazo_transporte_ocasional(fecha_entrega_transporte)

            lines = [
                f"**Modelo 308 — Sujeto ocasional medio de transporte nuevo — {year}**",
                "Supuesto: Art. 7.1.a Orden EHA/3786/2008 + Art. 25.uno y dos LIVA.",
                f"Plazo de presentacion: {plazo_label}",
                "",
                f"- IVA soportado al adquirir el medio de transporte: "
                f"{iva_soportado_transporte_nuevo:,.2f} EUR",
                f"- **A devolver: {cuota_devolver:,.2f} EUR**",
                "",
                "Como sujeto ocasional, solo puede solicitar la devolucion del "
                "IVA soportado al adquirir el medio de transporte que ahora "
                "entrega intracomunitariamente exento. No es una autoliquidacion "
                "periodica.",
            ]

            return {
                "success": True,
                "modelo": "308",
                "caso": caso_norm,
                "year": year,
                "plazo": plazo_label,
                "iva_a_devolver": cuota_devolver,
                "resultado": {
                    "tipo": "A devolver" if cuota_devolver > 0 else "Sin resultado",
                    "importe": cuota_devolver,
                },
                "formatted_response": "\n".join(lines),
            }

        # ===== CASO 2: TRANSPORTISTA REGIMEN SIMPLIFICADO =====
        if caso_norm == "transportista_simplificado":
            if iva_soportado_vehiculo_simplificado < 0:
                return {
                    "success": False,
                    "error": "iva_soportado_vehiculo_simplificado no puede ser negativo",
                    "formatted_response": (
                        "El IVA soportado en la adquisicion del vehiculo no " "puede ser negativo."
                    ),
                }
            cuota_devolver = round(iva_soportado_vehiculo_simplificado, 2)
            plazo_label = _calc_plazo_transportista(fecha_adquisicion_vehiculo)

            lines = [
                f"**Modelo 308 — Transportista regimen simplificado — {year}**",
                "Supuesto: Art. 7.1.b Orden EHA/3786/2008.",
                f"Plazo de presentacion: {plazo_label}",
                "",
                f"- IVA soportado deducible en el vehiculo afecto: "
                f"{iva_soportado_vehiculo_simplificado:,.2f} EUR",
                f"- **A devolver: {cuota_devolver:,.2f} EUR**",
                "",
                "El transportista en regimen simplificado de IVA puede solicitar "
                "via Modelo 308 la devolucion del IVA soportado deducible en la "
                "adquisicion de vehiculos afectos a la actividad de transporte "
                "de viajeros o mercancias por carretera.",
            ]

            return {
                "success": True,
                "modelo": "308",
                "caso": caso_norm,
                "year": year,
                "plazo": plazo_label,
                "iva_a_devolver": cuota_devolver,
                "resultado": {
                    "tipo": "A devolver" if cuota_devolver > 0 else "Sin resultado",
                    "importe": cuota_devolver,
                },
                "formatted_response": "\n".join(lines),
            }

        # ===== CASO 3: RE — TAX-FREE A VIAJEROS =====
        if caso_norm == "re_viajeros":
            if iva_devuelto_a_viajeros < 0:
                return {
                    "success": False,
                    "error": "iva_devuelto_a_viajeros no puede ser negativo",
                    "formatted_response": ("El IVA reembolsado a viajeros no puede ser negativo."),
                }
            periodos_validos = {"1T", "2T", "3T", "4T"}
            periodo_upper = (periodo or "").upper().strip()
            if periodo_upper not in periodos_validos:
                return {
                    "success": False,
                    "error": "Periodo debe ser '1T', '2T', '3T' o '4T'",
                    "formatted_response": (
                        "El caso 're_viajeros' requiere indicar el trimestre "
                        "(1T, 2T, 3T o 4T) en el que se efectuaron las "
                        "devoluciones a viajeros."
                    ),
                }

            cuota_devolver = round(iva_devuelto_a_viajeros, 2)
            plazo_label = _plazo_re_viajeros(periodo_upper)
            trimestre_meses = {
                "1T": "enero-marzo",
                "2T": "abril-junio",
                "3T": "julio-septiembre",
                "4T": "octubre-diciembre",
            }[periodo_upper]
            periodo_label = f"{periodo_upper} {year} ({trimestre_meses})"

            lines = [
                f"**Modelo 308 — RE devolucion IVA a viajeros (tax-free) — {periodo_label}**",
                "Supuesto: Art. 7.1.c Orden EHA/3786/2008 + Art. 21.2 LIVA.",
                f"Plazo de presentacion: {plazo_label}",
                "",
                f"- IVA reembolsado a viajeros extracomunitarios en el trimestre: "
                f"{iva_devuelto_a_viajeros:,.2f} EUR",
                f"- **A devolver: {cuota_devolver:,.2f} EUR**",
                "",
                "El comerciante minorista en Recargo de Equivalencia recupera "
                "via Modelo 308 las cantidades de IVA que ha reembolsado a "
                "turistas extracomunitarios en el regimen tax-free (compras con "
                "destino fuera de la UE).",
            ]

            return {
                "success": True,
                "modelo": "308",
                "caso": caso_norm,
                "periodo": periodo_upper,
                "year": year,
                "plazo": plazo_label,
                "iva_a_devolver": cuota_devolver,
                "resultado": {
                    "tipo": "A devolver" if cuota_devolver > 0 else "Sin resultado",
                    "importe": cuota_devolver,
                },
                "formatted_response": "\n".join(lines),
            }

        # No deberia llegar aqui (ya validado)
        return {
            "success": False,
            "error": f"Caso no implementado: {caso_norm}",
            "formatted_response": "Caso no soportado.",
        }

    except Exception as e:
        logger.error(f"Error calculating Modelo 308: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular el Modelo 308: {str(e)}",
        }
