"""
Modelo 308 (Solicitud de Devolucion del Recargo de Equivalencia) Tool for TaxIA

Calculates the IVA refund request for businesses in the Recargo de Equivalencia (RE)
regime in specific cases defined by Art. 30 bis.1 RIVA:

1. Adquisiciones intracomunitarias de bienes
2. Inversion del sujeto pasivo (ISP) en operaciones interiores
3. Entrega de medios de transporte nuevos intracomunitarios
4. Exportaciones y entregas intracomunitarias exentas

The RE regime applies primarily to retailers (comerciantes minoristas) who sell
to the end consumer without issuing invoices with IVA desglosado. Pharmacies
(farmacias) are a key example.

Based on AEAT instructions for Modelo 308.
Does NOT generate flat files — only computes amounts.
"""
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# IVA + RE rates (2025)
# Each tuple: (iva_rate, re_rate)
TIPOS_RE = {
    "general": (0.21, 0.052),
    "reducido": (0.10, 0.014),
    "superreducido": (0.04, 0.005),
}

MODELO_308_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_308",
        "description": """SIEMPRE DEBES USAR ESTA FUNCION cuando el usuario pregunte sobre:
- Modelo 308
- Devolucion del Recargo de Equivalencia
- Solicitud de devolucion IVA en recargo de equivalencia
- Adquisiciones intracomunitarias en recargo de equivalencia
- Inversion del sujeto pasivo en recargo de equivalencia
- IVA soportado por farmacia en adquisiciones intracomunitarias
- Exportaciones de comerciantes minoristas en RE

OBLIGATORIO usar esta funcion si el usuario es comerciante minorista
(farmacia, estanco, kiosco, etc.) en regimen de recargo de equivalencia
y pregunta por devolucion de IVA soportado en operaciones especificas.

El Modelo 308 permite solicitar la devolucion del IVA y recargo de equivalencia
soportado en:
- Adquisiciones intracomunitarias de bienes (Art. 30 bis.1 RIVA)
- Operaciones con inversion del sujeto pasivo (ISP)
- Entregas intracomunitarias exentas de medios de transporte nuevos
- Exportaciones y entregas intracomunitarias exentas

NO confundir con el Modelo 303 (autoliquidacion IVA trimestral del regimen general).
El 308 es EXCLUSIVO para sujetos pasivos en RE que no presentan 303.""",
        "parameters": {
            "type": "object",
            "properties": {
                "periodo": {
                    "type": "string",
                    "description": "Periodo de la solicitud. Formato: '1T', '2T', '3T', '4T' para trimestral, o '0A' para anual. Los comerciantes en RE normalmente presentan anual (0A)."
                },
                "year": {
                    "type": "integer",
                    "description": "Ano fiscal. Por defecto: ano actual"
                },
                "base_intracomunitarias_21": {
                    "type": "number",
                    "description": "Base imponible de adquisiciones intracomunitarias al tipo general (21%). Por defecto: 0"
                },
                "base_intracomunitarias_10": {
                    "type": "number",
                    "description": "Base imponible de adquisiciones intracomunitarias al tipo reducido (10%). Por defecto: 0"
                },
                "base_intracomunitarias_4": {
                    "type": "number",
                    "description": "Base imponible de adquisiciones intracomunitarias al tipo superreducido (4%). Por defecto: 0"
                },
                "base_isp_21": {
                    "type": "number",
                    "description": "Base imponible de operaciones con inversion del sujeto pasivo al 21%. Por defecto: 0"
                },
                "base_isp_10": {
                    "type": "number",
                    "description": "Base imponible de operaciones con inversion del sujeto pasivo al 10%. Por defecto: 0"
                },
                "base_isp_4": {
                    "type": "number",
                    "description": "Base imponible de operaciones con inversion del sujeto pasivo al 4%. Por defecto: 0"
                },
                "base_exportaciones": {
                    "type": "number",
                    "description": "Base imponible de exportaciones y entregas intracomunitarias exentas. Permite recuperar el RE soportado en compras destinadas a exportacion. Por defecto: 0"
                },
                "re_soportado_exportaciones": {
                    "type": "number",
                    "description": "Recargo de equivalencia soportado en bienes destinados a exportacion/entrega intracomunitaria exenta. Por defecto: 0"
                },
                "base_transporte_nuevo": {
                    "type": "number",
                    "description": "Base imponible de entrega intracomunitaria de medios de transporte nuevos. Por defecto: 0"
                },
                "iva_soportado_transporte": {
                    "type": "number",
                    "description": "IVA + RE soportado en la adquisicion del medio de transporte nuevo. Por defecto: 0"
                },
                "compensacion_periodos_anteriores": {
                    "type": "number",
                    "description": "Cuotas a compensar de periodos anteriores (>= 0). Por defecto: 0"
                }
            },
            "required": ["periodo"]
        }
    }
}


async def calculate_modelo_308_tool(
    periodo: str,
    year: int = None,
    base_intracomunitarias_21: float = 0,
    base_intracomunitarias_10: float = 0,
    base_intracomunitarias_4: float = 0,
    base_isp_21: float = 0,
    base_isp_10: float = 0,
    base_isp_4: float = 0,
    base_exportaciones: float = 0,
    re_soportado_exportaciones: float = 0,
    base_transporte_nuevo: float = 0,
    iva_soportado_transporte: float = 0,
    compensacion_periodos_anteriores: float = 0,
    restricted_mode: bool = False,
) -> Dict[str, Any]:
    """
    Calculate the Modelo 308 refund request for businesses in the
    Recargo de Equivalencia (RE) regime.

    Covers four types of qualifying operations:
    1. Adquisiciones intracomunitarias (Art. 30 bis.1 RIVA)
    2. Inversion del sujeto pasivo (ISP)
    3. Exportaciones y entregas intracomunitarias exentas
    4. Entregas intracomunitarias de medios de transporte nuevos

    Args:
        periodo: '1T'-'4T' for quarterly, '0A' for annual
        year: Fiscal year (default: current)
        base_intracomunitarias_21: Intra-community acquisitions base at 21%
        base_intracomunitarias_10: Intra-community acquisitions base at 10%
        base_intracomunitarias_4: Intra-community acquisitions base at 4%
        base_isp_21: Reverse charge operations base at 21%
        base_isp_10: Reverse charge operations base at 10%
        base_isp_4: Reverse charge operations base at 4%
        base_exportaciones: Exports/exempt intra-community supplies base
        re_soportado_exportaciones: RE borne on goods destined for export
        base_transporte_nuevo: New means of transport intra-community supply
        iva_soportado_transporte: IVA+RE borne on the new transport acquisition
        compensacion_periodos_anteriores: Amounts to offset from prior periods
        restricted_mode: If True, block (salaried-only plan)

    Returns:
        Dict with calculation results and formatted response
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

        # Validate periodo
        periodos_validos = {"1T", "2T", "3T", "4T", "0A"}
        periodo_upper = periodo.upper().strip()
        if periodo_upper not in periodos_validos:
            return {
                "success": False,
                "error": "Periodo debe ser '1T', '2T', '3T', '4T' o '0A'",
                "formatted_response": (
                    "El periodo debe ser un trimestre (1T, 2T, 3T, 4T) "
                    "o anual (0A)."
                ),
            }

        # Validate no negative bases
        bases = {
            "base_intracomunitarias_21": base_intracomunitarias_21,
            "base_intracomunitarias_10": base_intracomunitarias_10,
            "base_intracomunitarias_4": base_intracomunitarias_4,
            "base_isp_21": base_isp_21,
            "base_isp_10": base_isp_10,
            "base_isp_4": base_isp_4,
            "base_exportaciones": base_exportaciones,
            "base_transporte_nuevo": base_transporte_nuevo,
        }
        for name, val in bases.items():
            if val < 0:
                return {
                    "success": False,
                    "error": f"{name} no puede ser negativo",
                    "formatted_response": (
                        f"La base imponible '{name}' no puede ser negativa. "
                        f"Valor recibido: {val:,.2f} EUR."
                    ),
                }

        if re_soportado_exportaciones < 0:
            return {
                "success": False,
                "error": "re_soportado_exportaciones no puede ser negativo",
                "formatted_response": (
                    "El recargo de equivalencia soportado en exportaciones "
                    "no puede ser negativo."
                ),
            }

        if iva_soportado_transporte < 0:
            return {
                "success": False,
                "error": "iva_soportado_transporte no puede ser negativo",
                "formatted_response": (
                    "El IVA soportado en medios de transporte "
                    "no puede ser negativo."
                ),
            }

        compensacion_periodos_anteriores = max(compensacion_periodos_anteriores, 0)

        # ===== 1. ADQUISICIONES INTRACOMUNITARIAS =====
        # The RE subject must self-assess IVA + RE on intra-community acquisitions
        # and then request refund of that amount (since they cannot deduct via 303)
        cuota_intra_21_iva = round(base_intracomunitarias_21 * 0.21, 2)
        cuota_intra_21_re = round(base_intracomunitarias_21 * 0.052, 2)
        cuota_intra_10_iva = round(base_intracomunitarias_10 * 0.10, 2)
        cuota_intra_10_re = round(base_intracomunitarias_10 * 0.014, 2)
        cuota_intra_4_iva = round(base_intracomunitarias_4 * 0.04, 2)
        cuota_intra_4_re = round(base_intracomunitarias_4 * 0.005, 2)

        total_cuota_intra_iva = round(
            cuota_intra_21_iva + cuota_intra_10_iva + cuota_intra_4_iva, 2
        )
        total_cuota_intra_re = round(
            cuota_intra_21_re + cuota_intra_10_re + cuota_intra_4_re, 2
        )
        total_base_intra = round(
            base_intracomunitarias_21 + base_intracomunitarias_10
            + base_intracomunitarias_4, 2
        )

        # ===== 2. INVERSION DEL SUJETO PASIVO =====
        cuota_isp_21_iva = round(base_isp_21 * 0.21, 2)
        cuota_isp_21_re = round(base_isp_21 * 0.052, 2)
        cuota_isp_10_iva = round(base_isp_10 * 0.10, 2)
        cuota_isp_10_re = round(base_isp_10 * 0.014, 2)
        cuota_isp_4_iva = round(base_isp_4 * 0.04, 2)
        cuota_isp_4_re = round(base_isp_4 * 0.005, 2)

        total_cuota_isp_iva = round(
            cuota_isp_21_iva + cuota_isp_10_iva + cuota_isp_4_iva, 2
        )
        total_cuota_isp_re = round(
            cuota_isp_21_re + cuota_isp_10_re + cuota_isp_4_re, 2
        )
        total_base_isp = round(
            base_isp_21 + base_isp_10 + base_isp_4, 2
        )

        # ===== 3. EXPORTACIONES Y ENTREGAS INTRACOMUNITARIAS EXENTAS =====
        # The RE borne on goods that are exported can be recovered
        cuota_exportaciones_re = round(re_soportado_exportaciones, 2)

        # ===== 4. MEDIOS DE TRANSPORTE NUEVOS =====
        cuota_transporte = round(iva_soportado_transporte, 2)

        # ===== TOTALS =====
        # IVA devengado (autoliquidacion): must be paid
        total_iva_devengado = round(total_cuota_intra_iva + total_cuota_isp_iva, 2)
        total_re_devengado = round(total_cuota_intra_re + total_cuota_isp_re, 2)

        # IVA + RE a devolver (same amounts, since RE subjects self-assess and reclaim)
        total_iva_deducible = total_iva_devengado
        total_re_deducible = total_re_devengado

        # Additional refundable amounts
        total_adicional = round(cuota_exportaciones_re + cuota_transporte, 2)

        # Net result: additional refundable amounts minus compensation
        # The intra-community and ISP amounts net to zero (devengado = deducible)
        # Only exports RE and transport IVA generate a net refund
        resultado_previo = round(total_adicional, 2)
        resultado_final = round(resultado_previo - compensacion_periodos_anteriores, 2)

        # Determine result type
        if resultado_final > 0:
            tipo_resultado = "A devolver"
        elif resultado_final == 0:
            tipo_resultado = "Sin resultado"
        else:
            tipo_resultado = "A compensar"

        # Period label
        if periodo_upper == "0A":
            periodo_label = f"Anual {year}"
        else:
            trimestre_num = int(periodo_upper[0])
            trimestre_meses = {
                1: "enero-marzo",
                2: "abril-junio",
                3: "julio-septiembre",
                4: "octubre-diciembre",
            }[trimestre_num]
            periodo_label = f"{periodo_upper} {year} ({trimestre_meses})"

        # ===== BUILD FORMATTED RESPONSE =====
        lines = []
        lines.append(
            f"**Modelo 308 — Solicitud de Devolucion RE — {periodo_label}**"
        )
        lines.append(
            "Presentacion: AEAT (sede.agenciatributaria.gob.es)"
        )
        lines.append("")

        has_intra = total_base_intra > 0
        has_isp = total_base_isp > 0
        has_export = base_exportaciones > 0 or re_soportado_exportaciones > 0
        has_transport = base_transporte_nuevo > 0 or iva_soportado_transporte > 0

        # Section: Adquisiciones intracomunitarias
        if has_intra:
            lines.append("**Adquisiciones intracomunitarias (Art. 30 bis.1 RIVA)**")
            if base_intracomunitarias_21 > 0:
                lines.append(
                    f"- Base 21%: {base_intracomunitarias_21:,.2f} EUR | "
                    f"IVA: {cuota_intra_21_iva:,.2f} EUR | "
                    f"RE 5,2%: {cuota_intra_21_re:,.2f} EUR"
                )
            if base_intracomunitarias_10 > 0:
                lines.append(
                    f"- Base 10%: {base_intracomunitarias_10:,.2f} EUR | "
                    f"IVA: {cuota_intra_10_iva:,.2f} EUR | "
                    f"RE 1,4%: {cuota_intra_10_re:,.2f} EUR"
                )
            if base_intracomunitarias_4 > 0:
                lines.append(
                    f"- Base 4%: {base_intracomunitarias_4:,.2f} EUR | "
                    f"IVA: {cuota_intra_4_iva:,.2f} EUR | "
                    f"RE 0,5%: {cuota_intra_4_re:,.2f} EUR"
                )
            lines.append(
                f"- **Total IVA intracomunitario: {total_cuota_intra_iva:,.2f} EUR | "
                f"Total RE: {total_cuota_intra_re:,.2f} EUR**"
            )
            lines.append("")

        # Section: Inversion del sujeto pasivo
        if has_isp:
            lines.append("**Inversion del sujeto pasivo (ISP)**")
            if base_isp_21 > 0:
                lines.append(
                    f"- Base 21%: {base_isp_21:,.2f} EUR | "
                    f"IVA: {cuota_isp_21_iva:,.2f} EUR | "
                    f"RE 5,2%: {cuota_isp_21_re:,.2f} EUR"
                )
            if base_isp_10 > 0:
                lines.append(
                    f"- Base 10%: {base_isp_10:,.2f} EUR | "
                    f"IVA: {cuota_isp_10_iva:,.2f} EUR | "
                    f"RE 1,4%: {cuota_isp_10_re:,.2f} EUR"
                )
            if base_isp_4 > 0:
                lines.append(
                    f"- Base 4%: {base_isp_4:,.2f} EUR | "
                    f"IVA: {cuota_isp_4_iva:,.2f} EUR | "
                    f"RE 0,5%: {cuota_isp_4_re:,.2f} EUR"
                )
            lines.append(
                f"- **Total IVA ISP: {total_cuota_isp_iva:,.2f} EUR | "
                f"Total RE: {total_cuota_isp_re:,.2f} EUR**"
            )
            lines.append("")

        # Section: Exportaciones
        if has_export:
            lines.append(
                "**Exportaciones y entregas intracomunitarias exentas**"
            )
            if base_exportaciones > 0:
                lines.append(
                    f"- Base exportaciones: {base_exportaciones:,.2f} EUR"
                )
            lines.append(
                f"- RE soportado recuperable: {cuota_exportaciones_re:,.2f} EUR"
            )
            lines.append("")

        # Section: Medios de transporte nuevos
        if has_transport:
            lines.append(
                "**Entrega intracomunitaria de medios de transporte nuevos**"
            )
            lines.append(
                f"- Base medio de transporte: {base_transporte_nuevo:,.2f} EUR"
            )
            lines.append(
                f"- IVA+RE soportado recuperable: {cuota_transporte:,.2f} EUR"
            )
            lines.append("")

        # Resultado
        lines.append("**Resultado**")
        if has_intra or has_isp:
            lines.append(
                f"- IVA devengado (autoliquidacion): "
                f"{total_iva_devengado:,.2f} EUR"
            )
            lines.append(
                f"- RE devengado: {total_re_devengado:,.2f} EUR"
            )
            lines.append(
                f"- IVA deducible (= devengado): "
                f"{total_iva_deducible:,.2f} EUR"
            )
            lines.append(
                f"- RE deducible (= devengado): "
                f"{total_re_deducible:,.2f} EUR"
            )
        if total_adicional > 0:
            lines.append(
                f"- Cuotas adicionales a devolver: "
                f"{total_adicional:,.2f} EUR"
            )
        if compensacion_periodos_anteriores > 0:
            lines.append(
                f"- Compensacion periodos anteriores: "
                f"-{compensacion_periodos_anteriores:,.2f} EUR"
            )
        lines.append(
            f"- **Resultado final: {resultado_final:,.2f} EUR — "
            f"{tipo_resultado}**"
        )

        # Explanatory notes
        lines.append("")
        if has_intra:
            lines.append(
                "En las adquisiciones intracomunitarias, el comerciante en RE "
                "debe autoliquidar el IVA + RE (como sujeto pasivo por "
                "inversion), y a la vez tiene derecho a solicitar la devolucion "
                "de esas mismas cuotas mediante el Modelo 308."
            )
        if has_isp:
            lines.append(
                "En operaciones con inversion del sujeto pasivo, el mecanismo "
                "es analogo: se autoliquida y se solicita devolucion."
            )
        if has_export:
            lines.append(
                "En exportaciones, se recupera el RE soportado en la compra "
                "de bienes que se exportan (Art. 153.dos LIVA)."
            )

        lines.append("")
        lines.append(
            "El Modelo 308 es exclusivo para sujetos pasivos en regimen de "
            "Recargo de Equivalencia (RE). No sustituye al Modelo 303 "
            "(regimen general de IVA) ni al Modelo 309. "
            "Plazo de presentacion: los 20 primeros dias del mes siguiente "
            "al periodo (o 30 de enero para el 4T/anual)."
        )

        formatted_response = "\n".join(lines)

        logger.info(
            f"Modelo 308 calculated: {periodo_upper} {year}, "
            f"iva_devengado={total_iva_devengado}, "
            f"re_devengado={total_re_devengado}, "
            f"adicional={total_adicional}, "
            f"resultado={resultado_final} ({tipo_resultado})"
        )

        return {
            "success": True,
            "periodo": periodo_upper,
            "year": year,
            "modelo": "308",
            "regimen": "Recargo de Equivalencia",
            "adquisiciones_intracomunitarias": {
                "base_total": total_base_intra,
                "cuota_iva": total_cuota_intra_iva,
                "cuota_re": total_cuota_intra_re,
                "desglose": {
                    "base_21": base_intracomunitarias_21,
                    "iva_21": cuota_intra_21_iva,
                    "re_21": cuota_intra_21_re,
                    "base_10": base_intracomunitarias_10,
                    "iva_10": cuota_intra_10_iva,
                    "re_10": cuota_intra_10_re,
                    "base_4": base_intracomunitarias_4,
                    "iva_4": cuota_intra_4_iva,
                    "re_4": cuota_intra_4_re,
                },
            },
            "inversion_sujeto_pasivo": {
                "base_total": total_base_isp,
                "cuota_iva": total_cuota_isp_iva,
                "cuota_re": total_cuota_isp_re,
                "desglose": {
                    "base_21": base_isp_21,
                    "iva_21": cuota_isp_21_iva,
                    "re_21": cuota_isp_21_re,
                    "base_10": base_isp_10,
                    "iva_10": cuota_isp_10_iva,
                    "re_10": cuota_isp_10_re,
                    "base_4": base_isp_4,
                    "iva_4": cuota_isp_4_iva,
                    "re_4": cuota_isp_4_re,
                },
            },
            "exportaciones": {
                "base": base_exportaciones,
                "re_soportado": cuota_exportaciones_re,
            },
            "transporte_nuevo": {
                "base": base_transporte_nuevo,
                "iva_re_soportado": cuota_transporte,
            },
            "resultado": {
                "iva_devengado": total_iva_devengado,
                "re_devengado": total_re_devengado,
                "iva_deducible": total_iva_deducible,
                "re_deducible": total_re_deducible,
                "cuotas_adicionales": total_adicional,
                "compensacion_anterior": compensacion_periodos_anteriores,
                "resultado_final": resultado_final,
                "tipo": tipo_resultado,
            },
            "formatted_response": formatted_response,
        }

    except Exception as e:
        logger.error(f"Error calculating Modelo 308: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular el Modelo 308: {str(e)}",
        }
