"""
IRPF Calculator Tool for TaxIA

Provides function calling capability for the LLM to calculate
exact IRPF (Spanish income tax) based on income and region.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Tool definition for OpenAI function calling
IRPF_CALCULATOR_TOOL = {
	"type": "function",
	"function": {
		"name": "calculate_irpf",
		"description": """SIEMPRE DEBES USAR ESTA FUNCIÓN cuando el usuario pregunte sobre:
- IRPF (Impuesto sobre la Renta de las Personas Físicas)
- Retención de IRPF
- Cuánto pago de impuestos sobre ingresos
- Renta
- Declaración de la renta

OBLIGATORIO usar esta función si el usuario menciona:
- Ingresos anuales o mensuales (ej: "gano 30.000€ al año", "cobro 2.500€/mes")
- Región/CCAA (ej: "en Madrid", "en Cataluña", "en Andalucía")
- Situación personal (soltero, casado, hijos, etc.)

NO respondas con información aproximada del contexto RAG.
SIEMPRE calcula el IRPF exacto con esta función.

La función calcula el IRPF exacto en España según los ingresos anuales, la comunidad autónoma y la situación personal. Devuelve el importe a pagar, el tipo efectivo y el desglose por tramos.""",
		"parameters": {
			"type": "object",
			"properties": {
				"base_imponible": {
					"type": "number",
					"description": "Base imponible anual en euros (ingresos totales después de reducciones)"
				},
				"comunidad_autonoma": {
					"type": "string",
					"description": "Comunidad autónoma del contribuyente (ej: 'Madrid', 'Cataluña', 'Andalucía'). Afecta a la escala autonómica del IRPF."
				},
				"estado_civil": {
					"type": "string",
					"enum": ["soltero", "casado"],
					"description": "Estado civil del contribuyente. Por defecto: 'soltero'"
				},
				"hijos": {
					"type": "integer",
					"description": "Número de hijos a cargo. Por defecto: 0"
				},
				"year": {
					"type": "integer",
					"description": "Año fiscal. Por defecto: 2024"
				}
			},
			"required": ["base_imponible", "comunidad_autonoma"]
		}
	}
}


async def calculate_irpf_tool(
	base_imponible: float,
	comunidad_autonoma: str,
	estado_civil: str = "soltero",
	hijos: int = 0,
	year: int = 2024
) -> Dict[str, Any]:
	"""
	Calculate IRPF based on taxable income and region.
	
	Args:
		base_imponible: Annual taxable income in euros
		comunidad_autonoma: Autonomous community
		estado_civil: Marital status (soltero, casado)
		hijos: Number of children
		year: Tax year (default 2024)
		
	Returns:
		Dict with IRPF calculation and formatted response
	"""
	try:
		from app.utils.irpf_calculator import IRPFCalculator
		
		# Initialize calculator
		calculator = IRPFCalculator()
		
		# Calculate IRPF
		result = calculator.calculate(
			base_imponible=base_imponible,
			comunidad_autonoma=comunidad_autonoma,
			estado_civil=estado_civil,
			hijos=hijos,
			year=year
		)
		
		if not result.get("success", False):
			return {
				"success": False,
				"error": result.get("error", "Error desconocido"),
				"formatted_response": f"❌ Error al calcular IRPF: {result.get('error', 'Error desconocido')}"
			}
		
		# Format response
		cuota_estatal = result.get("cuota_estatal", 0)
		cuota_autonomica = result.get("cuota_autonomica", 0)
		cuota_total = result.get("cuota_total", 0)
		tipo_efectivo = result.get("tipo_efectivo", 0)
		
		formatted_response = f"""✅ **Cálculo de IRPF {year}**

📊 **Base imponible**: {base_imponible:,.2f}€
📍 **Comunidad Autónoma**: {comunidad_autonoma}
👤 **Situación**: {estado_civil}, {hijos} hijo{'s' if hijos != 1 else ''}

💰 **Resultado**:
- Cuota estatal: {cuota_estatal:,.2f}€
- Cuota autonómica: {cuota_autonomica:,.2f}€
- **TOTAL a pagar**: {cuota_total:,.2f}€

📈 **Tipo efectivo**: {tipo_efectivo:.2f}%

💡 **¿Qué significa esto?**
- De tus {base_imponible:,.2f}€ de base imponible, pagarás {cuota_total:,.2f}€ de IRPF
- Tu tipo efectivo es {tipo_efectivo:.2f}% (lo que realmente pagas sobre tus ingresos)
- Esto es orientativo. El cálculo final depende de deducciones, reducciones y circunstancias personales

⚠️ **Recuerda**: Esta es la cuota íntegra. Puedes aplicar deducciones (vivienda, donativos, etc.) que reducirán el importe final.
"""
		
		return {
			"success": True,
			"cuota_total": cuota_total,
			"cuota_estatal": cuota_estatal,
			"cuota_autonomica": cuota_autonomica,
			"tipo_efectivo": tipo_efectivo,
			"year": year,
			"formatted_response": formatted_response
		}
		
	except Exception as e:
		logger.error(f"Error calculating IRPF: {e}", exc_info=True)
		return {
			"success": False,
			"error": str(e),
			"formatted_response": f"❌ Error al calcular IRPF: {str(e)}"
		}