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

NO respondas con información aproximada del contexto RAG.
SIEMPRE calcula el IRPF exacto con esta función.

La función calcula el IRPF exacto en España según los ingresos anuales y la comunidad autónoma. Devuelve el importe a pagar, el tipo efectivo y el desglose por tramos.""",
		"parameters": {
			"type": "object",
			"properties": {
				"base_imponible": {
					"type": "number",
					"description": "Base imponible anual en euros (ingresos totales después de reducciones). Si el usuario da ingresos mensuales, multiplica por 12."
				},
				"comunidad_autonoma": {
					"type": "string",
					"description": "Comunidad autónoma del contribuyente (ej: 'Madrid', 'Cataluña', 'Andalucía', 'Aragón'). Afecta a la escala autonómica del IRPF. Usa el nombre exacto de la CCAA."
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
	year: int = 2024
) -> Dict[str, Any]:
	"""
	Calculate IRPF based on taxable income and region.
	
	Args:
		base_imponible: Annual taxable income in euros
		comunidad_autonoma: Autonomous community name
		year: Tax year (default 2024)
		
	Returns:
		Dict with IRPF calculation and formatted response
	"""
	try:
		from app.utils.irpf_calculator import IRPFCalculator
		
		# Initialize calculator
		calculator = IRPFCalculator()
		
		# Calculate IRPF
		result = await calculator.calculate_irpf(
			base_liquidable=base_imponible,
			jurisdiction=comunidad_autonoma,
			year=year,
			include_state=True
		)
		
		# Disconnect after use
		await calculator.disconnect()
		
		if not result:
			return {
				"success": False,
				"error": "Error en el cálculo",
				"formatted_response": "❌ Error al calcular IRPF: No se pudo obtener el resultado"
			}
		
		# Format response
		cuota_estatal = result.get("cuota_estatal", 0)
		cuota_autonomica = result.get("cuota_autonomica", 0)
		cuota_total = result.get("cuota_total", 0)
		tipo_medio = result.get("tipo_medio", 0)
		
		formatted_response = f"""✅ **Cálculo de IRPF {year}**

📊 **Base imponible**: {base_imponible:,.2f}€
📍 **Comunidad Autónoma**: {comunidad_autonoma}

💰 **Resultado**:
- Cuota estatal: {cuota_estatal:,.2f}€
- Cuota autonómica: {cuota_autonomica:,.2f}€
- **TOTAL a pagar**: {cuota_total:,.2f}€

📈 **Tipo medio efectivo**: {tipo_medio:.2f}%

💡 **¿Qué significa esto?**
- De tus {base_imponible:,.2f}€ de base imponible, pagarás {cuota_total:,.2f}€ de IRPF
- Tu tipo medio efectivo es {tipo_medio:.2f}% (lo que realmente pagas sobre tus ingresos)
- Esto es la cuota íntegra antes de deducciones

⚠️ **Recuerda**: 
- Esta es la cuota íntegra. Puedes aplicar deducciones (vivienda, donativos, etc.) que reducirán el importe final
- Si eres asalariado, tu empresa ya te retiene mensualmente. Esta cifra es orientativa para tu declaración anual
- Los parámetros exactos (reducciones, mínimo personal/familiar) varían según tu situación personal"""
		
		return {
			"success": True,
			"cuota_total": cuota_total,
			"cuota_estatal": cuota_estatal,
			"cuota_autonomica": cuota_autonomica,
			"tipo_medio": tipo_medio,
			"year": year,
			"formatted_response": formatted_response
		}
		
	except ValueError as ve:
		# Specific error (e.g., jurisdiction not found)
		logger.error(f"ValueError calculating IRPF: {ve}", exc_info=True)
		return {
			"success": False,
			"error": str(ve),
			"formatted_response": f"""❌ **Error en el cálculo de IRPF**

No se encontró información para **{comunidad_autonoma}** en el año {year}.

💡 **Posibles causas**:
- El nombre de la comunidad autónoma no es exacto
- No hay datos para ese año en la base de datos

📝 **Comunidades disponibles**: Madrid, Cataluña, Andalucía, Aragón, Asturias, Baleares, Canarias, Cantabria, Castilla y León, Castilla-La Mancha, Extremadura, Galicia, La Rioja, Murcia, Valencia

⚠️ **Nota**: Navarra y País Vasco tienen regímenes forales propios que no están en este cálculo."""
		}
	except Exception as e:
		logger.error(f"Error calculating IRPF: {e}", exc_info=True)
		return {
			"success": False,
			"error": str(e),
			"formatted_response": f"❌ Error al calcular IRPF: {str(e)}"
		}