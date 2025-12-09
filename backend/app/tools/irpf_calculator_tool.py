"""
IRPF Calculator Tool for Microsoft Agent Framework.

This tool can be called by the TaxAgent to calculate exact IRPF
when the user asks about tax amounts for a specific region.
"""
from typing import Dict, Any
import logging

from app.utils.irpf_calculator import IRPFCalculator

logger = logging.getLogger(__name__)


async def calculate_irpf_tool(
    base_liquidable: float,
    jurisdiction: str,
    year: int = 2024
) -> Dict[str, Any]:
    """
    Calculate exact IRPF (Spanish Income Tax) using official tax scales.
    
    Use this tool when the user asks about how much IRPF they will pay
    given an amount and a location in Spain.
    
    Args:
        base_liquidable: Annual taxable income in euros (gross salary)
        jurisdiction: Spanish autonomous community (CCAA) name, e.g., 'Aragón', 'Madrid', 'Andalucía'
        year: Tax year (default: 2024)
    
    Returns:
        Dictionary with:
        - cuota_total: Total IRPF amount in euros
        - cuota_estatal: State quota
        - cuota_autonomica: Regional quota
        - tipo_medio: Effective tax rate percentage
        - formatted_response: Human-readable explanation
    
    Example:
        User: "Vivo en Zaragoza y gané 35000 euros, ¿cuánto pagaré de IRPF?"
        Tool call: calculate_irpf_tool(base_liquidable=35000, jurisdiction="Aragón", year=2024)
        Result: cuota_total=13994.25€, tipo_medio=39.98%
    """
    try:
        calculator = IRPFCalculator()
        result = await calculator.calculate_irpf(
            base_liquidable=base_liquidable,
            jurisdiction=jurisdiction,
            year=year
        )
        await calculator.disconnect()
        
        # Format response for agent
        formatted = f"""**Cálculo IRPF {year} - {jurisdiction}**

Base liquidable: {base_liquidable:,.0f}€

📊 Desglose:
• Cuota Estatal: {result['cuota_estatal']:,.2f}€
• Cuota Autonómica ({jurisdiction}): {result['cuota_autonomica']:,.2f}€

🎯 **TOTAL: {result['cuota_total']:,.2f}€** (Tipo medio: {result['tipo_medio']}%)

⚠️ IMPORTANTE: Este cálculo es orientativo. El IRPF real depende de:
- Situación familiar (hijos, ascendientes, discapacidad)
- Tipo exacto de rentas (trabajo, actividades, capital)
- Cotizaciones y gastos deducibles
- Mínimos personales y familiares aplicables
- Deducciones estatales y autonómicas
- Aportaciones a pensiones
- Régimen de tributación (individual/conjunta)

Los {base_liquidable:,.0f}€ se asumen como rendimientos brutos anuales (habitual en nóminas).

Para un cálculo exacto, usa el simulador oficial de la AEAT o consulta con un asesor fiscal."""

        return {
            'success': True,
            'cuota_total': result['cuota_total'],
            'cuota_estatal': result['cuota_estatal'],
            'cuota_autonomica': result['cuota_autonomica'],
            'tipo_medio': result['tipo_medio'],
            'jurisdiction': jurisdiction,
            'base_liquidable': base_liquidable,
            'year': year,
            'formatted_response': formatted
        }
        
    except Exception as e:
        logger.error(f"Error calculating IRPF: {e}")
        return {
            'success': False,
            'error': str(e),
            'formatted_response': f"No pude calcular el IRPF para {jurisdiction}. Error: {str(e)}"
        }


# Tool metadata for Agent Framework
IRPF_CALCULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_irpf",
        "description": "Calculate exact Spanish Income Tax (IRPF) using official tax scales for a given income amount and autonomous community. Use when user asks 'how much IRPF will I pay' with an amount and location.",
        "parameters": {
            "type": "object",
            "properties": {
                "base_liquidable": {
                    "type": "number",
                    "description": "Annual taxable income in euros (gross salary). Example: 35000"
                },
                "jurisdiction": {
                    "type": "string",
                    "description": "Spanish autonomous community (CCAA) name. Examples: 'Aragón', 'Madrid', 'Andalucía', 'Cataluña', 'Comunitat Valenciana'",
                    "enum": [
                        "Aragón",
                        "Andalucía",
                        "Asturias",
                        "Illes Balears",
                        "Canarias",
                        "Cantabria",
                        "Castilla y León",
                        "Castilla-La Mancha",
                        "Cataluña",
                        "Extremadura",
                        "Galicia",
                        "Comunidad de Madrid",
                        "Región de Murcia",
                        "La Rioja",
                        "Comunitat Valenciana",
                        "Estatal"
                    ]
                },
                "year": {
                    "type": "integer",
                    "description": "Tax year (default: 2024)",
                    "default": 2024
                }
            },
            "required": ["base_liquidable", "jurisdiction"]
        }
    }
}
