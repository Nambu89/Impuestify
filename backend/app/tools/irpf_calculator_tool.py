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
	Implements fallback system: BD local → Web extraction → Previous year
	
	Args:
		base_imponible: Annual taxable income in euros
		comunidad_autonoma: Autonomous community name
		year: Tax year (default 2024)
		
	Returns:
		Dict with IRPF calculation and formatted response
	"""
	try:
		from app.utils.irpf_calculator import IRPFCalculator
		from app.tools.web_scraper_tool import normalize_ccaa_name
		from app.tools.search_tool import search_tax_regulations_tool
		
		# Initialize calculator
		calculator = IRPFCalculator()
		
		# Normalize CCAA name
		ccaa_normalized = normalize_ccaa_name(comunidad_autonoma)
		logger.info(f"Calculating IRPF: {base_imponible}€, {ccaa_normalized}, {year}")
		
		# ATTEMPT 1: Calculate with local DB
		try:
			logger.info(f"Attempt 1: Using local database for {ccaa_normalized} {year}")
			result = await calculator.calculate_irpf(
				base_liquidable=base_imponible,
				jurisdiction=ccaa_normalized,
				year=year,
				include_state=True
			)
			
			await calculator.disconnect()
			
			# Success with local DB
			logger.info(f"✅ Successfully calculated with local DB")
			return _format_irpf_result(
				result,
				base_imponible=base_imponible,
				comunidad_autonoma=ccaa_normalized,
				year=year,
				source="Base de datos local"
			)
			
		except ValueError as e:
			logger.info(f"Local DB failed: {e}")
			
			# ATTEMPT 2: Search web and extract data
			logger.info(f"Attempt 2: Searching web for {ccaa_normalized} {year}")
			
			search_result = await search_tax_regulations_tool(
				query=f"tramos IRPF {year} {ccaa_normalized} escala autonómica comunidad autónoma",
				year=year,
				extract_data=True
			)
			
			if search_result.get("success") and search_result.get("tramos"):
				logger.info(f"✅ Successfully extracted data from web")
				
				# Calculate with web-extracted data
				tramos_autonomicos = search_result["tramos"]
				
				# Try to get state scale from DB
				tramos_estatales = None
				try:
					state_scale = await calculator._get_scale('Estatal', year)
					tramos_estatales = state_scale
				except:
					logger.warning(f"No state scale for {year}, using only autonomous scale")
				
				result = calculator.calculate_with_custom_scale(
					base_liquidable=base_imponible,
					tramos_autonomicos=tramos_autonomicos,
					tramos_estatales=tramos_estatales,
					year=year,
					jurisdiction=ccaa_normalized
				)
				
				await calculator.disconnect()
				
				return _format_irpf_result(
					result,
					base_imponible=base_imponible,
					comunidad_autonoma=ccaa_normalized,
					year=year,
					source=f"Web: {search_result.get('source_name', 'Fuente oficial')}",
					source_url=search_result.get('source_url'),
					source_title=search_result.get('source_title')
				)
			
			# ATTEMPT 3: Fallback to previous year
			logger.info(f"Attempt 3: Trying previous year ({year - 1})")
			
			try:
				result = await calculator.calculate_irpf(
					base_liquidable=base_imponible,
					jurisdiction=ccaa_normalized,
					year=year - 1,
					include_state=True
				)
				
				await calculator.disconnect()
				
				return _format_irpf_result(
					result,
					base_imponible=base_imponible,
					comunidad_autonoma=ccaa_normalized,
					year=year - 1,
					source=f"Base de datos local (año {year - 1})",
					warning=f"⚠️ No hay datos disponibles para {year}. Cálculo basado en {year - 1}."
				)
			
			except ValueError:
				logger.error(f"All attempts failed for {ccaa_normalized}")
				
				# ATTEMPT 4: Return error with helpful URLs
				await calculator.disconnect()
				
				return {
					"success": False,
					"error": f"No se encontraron datos de IRPF para {ccaa_normalized} {year}",
					"formatted_response": f"""❌ **No se pudo calcular el IRPF**

No encontré datos de IRPF para **{ccaa_normalized}** en {year}.

💡 **Intenté**:
1. Base de datos local → No disponible
2. Búsqueda web en AEAT/BOE → No se pudieron extraer datos
3. Año anterior ({year - 1}) → No disponible

📝 **Comunidades disponibles en BD**: Madrid, Cataluña, Andalucía, Aragón, Asturias, Baleares, Canarias, Cantabria, Castilla y León, Castilla-La Mancha, Extremadura, Galicia, La Rioja, Murcia, Valencia

🌐 **Consulta directamente**:
- AEAT: https://www.agenciatributaria.es
- BOE: https://www.boe.es

⚠️ **Nota**: Navarra y País Vasco tienen regímenes forales propios que no están en este cálculo."""
				}
	
	except Exception as e:
		logger.error(f"Error calculating IRPF: {e}", exc_info=True)
		return {
			"success": False,
			"error": str(e),
			"formatted_response": f"❌ Error al calcular IRPF: {str(e)}"
		}


def _format_irpf_result(
	result: Dict,
	base_imponible: float,
	comunidad_autonoma: str,
	year: int,
	source: str,
	source_url: str = None,
	source_title: str = None,
	warning: str = None
) -> Dict[str, Any]:
	"""
	Format IRPF calculation result for user display.
	
	Args:
		result: Calculation result from IRPFCalculator
		base_imponible: Base imponible used
		comunidad_autonoma: CCAA name
		year: Tax year
		source: Source description
		source_url: Optional source URL
		source_title: Optional source title
		warning: Optional warning message
		
	Returns:
		Formatted response dict
	"""
	cuota_estatal = result.get("cuota_estatal", 0)
	cuota_autonomica = result.get("cuota_autonomica", 0)
	cuota_total = result.get("cuota_total", 0)
	tipo_medio = result.get("tipo_medio", 0)
	
	# Build source citation
	source_citation = f"\n\n📄 **Fuente**: {source}"
	if source_url:
		source_citation += f"\n🔗 **URL**: {source_url}"
	if source_title:
		source_citation += f"\n📰 **Título**: {source_title}"
	
	# Build warning if present
	warning_text = f"\n\n{warning}" if warning else ""
	
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
- Esto es la cuota íntegra antes de deducciones{source_citation}{warning_text}

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
		"source": source,
		"source_url": source_url,
		"formatted_response": formatted_response
	}