"""
Modelo IPSI (Ceuta/Melilla) Calculator Tool for TaxIA

Calculates the quarterly IPSI self-assessment for self-employed / businesses
in Ceuta and Melilla. IPSI replaces IVA in these territories.

Based on Ley 8/1991 (Ceuta) and Ley 13/1996 (Melilla).
6 rate tiers: 0.5%, 1%, 2%, 4%, 8%, 10%.
"""
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

MODELO_IPSI_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_modelo_ipsi",
        "description": """SIEMPRE DEBES USAR ESTA FUNCION cuando el usuario pregunte sobre:
- IPSI (Impuesto sobre la Produccion, los Servicios y la Importacion)
- Impuesto indirecto de Ceuta o Melilla
- Declaracion trimestral de Ceuta o Melilla (NO IVA, es IPSI)
- Cuanto impuesto indirecto tengo que pagar en Ceuta/Melilla

OBLIGATORIO usar esta funcion si el usuario vive en Ceuta o Melilla y pregunta
sobre su declaracion trimestral de impuesto indirecto. En Ceuta y Melilla NO
se aplica IVA — se aplica IPSI.

Tipos IPSI: 0.5% (minimo), 1% (reducido), 2% (bonificado), 4% (general),
8% (incrementado), 10% (especial). La ordenanza fiscal de cada ciudad
determina que tipo aplica a cada bien/servicio.""",
        "parameters": {
            "type": "object",
            "properties": {
                "territorio": {
                    "type": "string",
                    "enum": ["Ceuta", "Melilla"],
                    "description": "Ciudad autonoma: Ceuta o Melilla"
                },
                "trimestre": {
                    "type": "integer",
                    "description": "Trimestre de la declaracion (1, 2, 3 o 4)"
                },
                "year": {
                    "type": "integer",
                    "description": "Ano fiscal. Por defecto: ano actual"
                },
                "base_4": {
                    "type": "number",
                    "description": "Base imponible al tipo general (4%). La mayoria de operaciones van aqui"
                },
                "base_0_5": {
                    "type": "number",
                    "description": "Base imponible al tipo minimo (0.5%). Por defecto: 0"
                },
                "base_1": {
                    "type": "number",
                    "description": "Base imponible al tipo reducido (1%). Por defecto: 0"
                },
                "base_2": {
                    "type": "number",
                    "description": "Base imponible al tipo bonificado (2%). Por defecto: 0"
                },
                "base_8": {
                    "type": "number",
                    "description": "Base imponible al tipo incrementado (8%). Por defecto: 0"
                },
                "base_10": {
                    "type": "number",
                    "description": "Base imponible al tipo especial (10%). Por defecto: 0"
                },
                "ipsi_deducible": {
                    "type": "number",
                    "description": "IPSI soportado deducible en compras de bienes y servicios corrientes"
                },
                "ipsi_deducible_inversion": {
                    "type": "number",
                    "description": "IPSI soportado deducible en bienes de inversion. Por defecto: 0"
                },
                "ipsi_deducible_importaciones": {
                    "type": "number",
                    "description": "IPSI soportado deducible en importaciones. Por defecto: 0"
                },
                "compensacion_periodos_anteriores": {
                    "type": "number",
                    "description": "Cuotas a compensar de periodos anteriores (>= 0). Por defecto: 0"
                }
            },
            "required": ["territorio", "trimestre", "base_4", "ipsi_deducible"]
        }
    }
}


async def calculate_modelo_ipsi_tool(
    territorio: str,
    trimestre: int,
    base_4: float,
    ipsi_deducible: float,
    year: int = None,
    base_0_5: float = 0,
    base_1: float = 0,
    base_2: float = 0,
    base_8: float = 0,
    base_10: float = 0,
    ipsi_deducible_inversion: float = 0,
    ipsi_deducible_importaciones: float = 0,
    compensacion_periodos_anteriores: float = 0,
    restricted_mode: bool = False,
) -> Dict[str, Any]:
    """Calculate the quarterly IPSI self-assessment for Ceuta/Melilla."""
    if restricted_mode:
        from app.security.content_restriction import get_autonomo_block_response
        logger.warning("calculate_modelo_ipsi called in restricted_mode — blocking")
        return {
            "success": False,
            "error": "restricted",
            "formatted_response": get_autonomo_block_response()
        }

    try:
        if year is None:
            year = datetime.now().year

        if trimestre not in (1, 2, 3, 4):
            return {
                "success": False,
                "error": "Trimestre debe ser 1, 2, 3 o 4",
                "formatted_response": "El trimestre debe ser 1, 2, 3 o 4."
            }

        if territorio not in ("Ceuta", "Melilla"):
            return {
                "success": False,
                "error": "Territorio debe ser 'Ceuta' o 'Melilla'",
                "formatted_response": "El IPSI solo aplica en Ceuta o Melilla."
            }

        compensacion_periodos_anteriores = max(compensacion_periodos_anteriores, 0)

        # Call calculator
        from app.utils.calculators.modelo_ipsi import ModeloIpsiCalculator
        calc = ModeloIpsiCalculator(None)
        result = await calc.calculate(
            territorio=territorio,
            base_0_5=base_0_5,
            base_1=base_1,
            base_2=base_2,
            base_4=base_4,
            base_8=base_8,
            base_10=base_10,
            cuota_corrientes_interiores=ipsi_deducible,
            cuota_inversion_interiores=ipsi_deducible_inversion,
            cuota_importaciones_corrientes=ipsi_deducible_importaciones,
            cuotas_compensar_anteriores=compensacion_periodos_anteriores,
            quarter=trimestre,
            year=year,
        )

        # Build formatted response
        total_devengado = result["total_devengado"]
        total_deducible = result["total_deducible"]
        resultado = result["resultado_liquidacion"]

        trimestre_label = {1: "1T", 2: "2T", 3: "3T", 4: "4T"}[trimestre]
        trimestre_meses = {
            1: "enero-marzo",
            2: "abril-junio",
            3: "julio-septiembre",
            4: "octubre-diciembre"
        }[trimestre]

        if resultado > 0:
            tipo_resultado = "A ingresar"
        elif resultado < 0:
            tipo_resultado = "A devolver" if trimestre == 4 else "A compensar"
        else:
            tipo_resultado = "Sin actividad"

        lines = []
        lines.append(f"**IPSI {territorio} — {trimestre_label} {year} ({trimestre_meses})**")
        lines.append("")

        # IPSI Devengado
        lines.append("**IPSI Devengado (repercutido)**")
        desglose = result["desglose_devengado"]
        rate_labels = [
            ("tipo_minimo_0_5", "0.5%"),
            ("tipo_reducido_1", "1%"),
            ("tipo_bonificado_2", "2%"),
            ("tipo_general_4", "4%"),
            ("tipo_incrementado_8", "8%"),
            ("tipo_especial_10", "10%"),
        ]
        for key, label in rate_labels:
            entry = desglose[key]
            if entry["base"] > 0:
                lines.append(
                    f"- Base {label}: {entry['base']:,.2f} EUR | "
                    f"Cuota: {entry['cuota']:,.2f} EUR"
                )
        imp = desglose["importaciones"]
        if imp["base"] > 0:
            lines.append(
                f"- Importaciones: {imp['base']:,.2f} EUR al "
                f"{imp['tipo']*100:.1f}% | Cuota: {imp['cuota']:,.2f} EUR"
            )
        isp = desglose["inversion_sujeto_pasivo"]
        if isp["base"] > 0:
            lines.append(
                f"- Inversion sujeto pasivo: {isp['base']:,.2f} EUR | "
                f"Cuota: {isp['cuota']:,.2f} EUR"
            )
        lines.append(f"- **Total devengado: {total_devengado:,.2f} EUR**")
        lines.append("")

        # IPSI Deducible
        lines.append("**IPSI Deducible (soportado)**")
        if ipsi_deducible > 0:
            lines.append(f"- Bienes y servicios corrientes: {ipsi_deducible:,.2f} EUR")
        if ipsi_deducible_inversion > 0:
            lines.append(f"- Bienes de inversion: {ipsi_deducible_inversion:,.2f} EUR")
        if ipsi_deducible_importaciones > 0:
            lines.append(f"- Importaciones: {ipsi_deducible_importaciones:,.2f} EUR")
        lines.append(f"- **Total a deducir: {total_deducible:,.2f} EUR**")
        lines.append("")

        # Resultado
        lines.append("**Resultado**")
        rg = result["resultado_regimen_general"]
        lines.append(f"- Resultado regimen general: {rg:,.2f} EUR")
        if compensacion_periodos_anteriores > 0:
            lines.append(f"- Compensacion periodos anteriores: -{compensacion_periodos_anteriores:,.2f} EUR")
        lines.append(f"- **Resultado final: {resultado:,.2f} EUR — {tipo_resultado}**")

        lines.append("")
        if resultado > 0:
            lines.append(
                f"Debes ingresar {resultado:,.2f} EUR a la Ciudad Autonoma de {territorio} "
                f"antes del dia 20 del mes siguiente al trimestre."
            )
        elif resultado < 0 and trimestre < 4:
            lines.append(
                f"El resultado negativo de {abs(resultado):,.2f} EUR se compensa "
                f"en el siguiente trimestre."
            )
        elif resultado < 0 and trimestre == 4:
            lines.append(
                f"En el 4T puedes solicitar la devolucion de {abs(resultado):,.2f} EUR."
            )

        lines.append("")
        lines.append(
            f"Nota: Los tipos aplicables dependen de la ordenanza fiscal vigente "
            f"de {territorio}. Consulta la ordenanza para confirmar los tipos "
            f"aplicables a tus operaciones."
        )

        formatted_response = "\n".join(lines)

        logger.info(
            f"IPSI calculated: {territorio} {trimestre_label} {year}, "
            f"devengado={total_devengado}, deducible={total_deducible}, "
            f"resultado={resultado} ({tipo_resultado})"
        )

        return {
            "success": True,
            **result,
            "formatted_response": formatted_response,
        }

    except Exception as e:
        logger.error(f"Error calculating IPSI: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "formatted_response": f"Error al calcular el IPSI: {str(e)}"
        }
