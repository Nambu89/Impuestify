"""
Autonomous Quota Calculator Tool for TaxIA

Provides function calling capability for the LLM to calculate
exact autonomous worker quotas based on income and region.
"""
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# Tool definition for OpenAI function calling
AUTONOMOUS_QUOTA_TOOL = {
	"type": "function",
	"function": {
		"name": "calculate_autonomous_quota",
		"description": """SIEMPRE DEBES USAR ESTA FUNCIÓN cuando el usuario pregunte sobre:
- Cuota de autónomos
- Cotización de autónomos  
- Cuánto paga un autónomo
- Cuánto tengo que pagar como autónomo
- Base de cotización

OBLIGATORIO usar esta función si el usuario menciona:
- Ingresos mensuales (ej: "gano 1500€", "ingreso 670€")
- Región (ej: "en Ceuta", "en Melilla", "en Madrid")

NO respondas con información aproximada del contexto RAG.
SIEMPRE calcula la cuota exacta con esta función.

⚠️ INTERPRETACIÓN CRÍTICA DE INGRESOS:
1. PREGUNTA DE CLARIFICACIÓN OBLIGATORIA si hay ambigüedad:
   - Si el usuario menciona una cantidad SIN especificar si es bruta o neta, PREGUNTA:
     "¿Esos [cantidad]€ son ingresos brutos (facturación total) o rendimientos netos (después de restar gastos)?"

2. INTERPRETACIÓN AUTOMÁTICA (solo si es claro):
   - Usuario dice "ingresos brutos", "facturación", "he facturado" 
     → Aplica deducción del 7%: cantidad × 0.93 = ingresos_netos_mensuales
   - Usuario dice "ingresos netos", "rendimientos netos", "después de gastos", "descontando gastos"
     → USA directamente: ingresos_netos_mensuales = cantidad (NO aplicar × 0.93)

3. EXPLICACIÓN AL USUARIO:
   Siempre explica qué valor usas:
   ✅ "Voy a calcular con 4.000€ de rendimientos netos mensuales (ya descontados gastos)"
   ✅ "Como son ingresos brutos, primero aplico la deducción: 5.000€ × 0.93 = 4.650€"

La función calcula la cuota mensual exacta de autónomos en España para 2025 según los ingresos netos mensuales y la región (general, Ceuta, o Melilla). Devuelve el tramo de cotización, la cuota mínima y máxima, y las bonificaciones aplicables.""",
		"parameters": {
			"type": "object",
			"properties": {
				"ingresos_netos_mensuales": {
					"type": "number",
					"description": "Rendimientos netos mensuales DESPUÉS de restar gastos y aplicar la deducción del 7% (solo si eran ingresos brutos). Si el usuario ya dijo 'ingresos netos' o 'después de gastos', usar ese valor directamente sin aplicar × 0.93."
				},
				"region": {
					"type": "string",
					"enum": ["general", "ceuta", "melilla"],
					"description": "Región del autónomo. Usar 'general' para toda España excepto Ceuta/Melilla. Ceuta y Melilla tienen bonificación del 50% en contingencias comunes. Por defecto: 'general'"
				},
				"year": {
					"type": "integer",
					"description": "Año de cotización. Por defecto: 2025"
				}
			},
			"required": ["ingresos_netos_mensuales"]
		}
	}
}


async def calculate_autonomous_quota_tool(
	ingresos_netos_mensuales: float,
	region: str = "general",
	year: int = 2025,
	restricted_mode: bool = False
) -> Dict[str, Any]:
	"""
	Calculate the autonomous worker quota based on net monthly income.

	Args:
		ingresos_netos_mensuales: Net monthly income in euros (AFTER expenses and 7% deduction if applicable)
		region: Region (general, ceuta, melilla)
		year: Year for calculation (default 2025)
		restricted_mode: If True, return restriction message instead of calculating

	Returns:
		Dict with quota information and formatted response
	"""
	# Safety net: block if called in restricted mode (salaried workers only)
	if restricted_mode:
		from app.security.content_restriction import get_autonomo_block_response
		logger.warning("calculate_autonomous_quota called in restricted_mode — blocking")
		return {
			"success": False,
			"error": "restricted",
			"formatted_response": get_autonomo_block_response()
		}

	try:
		from app.database.turso_client import TursoClient
		import os
		
		# Connect to database
		db = TursoClient(
			url=os.environ.get("TURSO_DATABASE_URL"),
			auth_token=os.environ.get("TURSO_AUTH_TOKEN")
		)
		await db.connect()
		
		# Query the autonomous_quotas table
		sql = """
		SELECT 
			tramo_number,
			rendimientos_netos_min,
			rendimientos_netos_max,
			base_cotizacion_min,
			base_cotizacion_max,
			cuota_min,
			cuota_max,
			bonificacion_percent,
			cuota_min_bonificada,
			cuota_max_bonificada
		FROM autonomous_quotas
		WHERE year = ?
		AND region = ?
		AND rendimientos_netos_min <= ?
		AND (rendimientos_netos_max >= ? OR rendimientos_netos_max IS NULL)
		LIMIT 1
		"""
		
		result = await db.execute(sql, [year, region, ingresos_netos_mensuales, ingresos_netos_mensuales])
		
		await db.disconnect()
		
		if not result.rows:
			# Determine if out of range
			if ingresos_netos_mensuales < 670:
				return {
					"success": False,
					"error": f"Ingresos muy bajos: {ingresos_netos_mensuales}€/mes",
					"formatted_response": f"""❌ **Ingresos muy bajos**

Tus ingresos declarados son **{ingresos_netos_mensuales}€/mes**, por debajo del **tramo mínimo** (670€/mes).

💡 **¿Qué significa esto?**
- Si tus ingresos netos están por debajo de 670€/mes, igualmente cotizarás por el **Tramo 1** (base mínima 653,59€)
- La cuota mínima sería aproximadamente **200€/mes**

⚠️ **Importante**: Aunque tus ingresos sean bajos, la cuota mínima de autónomos es obligatoria. Consulta con la Seguridad Social sobre posibles bonificaciones (tarifa plana, nuevos autónomos, etc.).

📞 **Recursos**:
- Seguridad Social: sede.seg-social.gob.es
- Tarifa plana nuevos autónomos: 80€/mes los primeros 12 meses"""
				}
			else:
				return {
					"success": False,
					"error": f"No se encontró un tramo de cotización para {ingresos_netos_mensuales}€ en {year}",
					"formatted_response": f"❌ No encontré información de cotización para ingresos de {ingresos_netos_mensuales}€/mes en {year}. Verifica que el importe sea correcto o consulta directamente con la Seguridad Social."
				}
		
		row = result.rows[0]
		
		# Extract data
		tramo = row['tramo_number']
		cuota_min = row['cuota_min']
		cuota_max = row['cuota_max']
		bonificacion = row['bonificacion_percent'] or 0
		cuota_min_bonificada = row['cuota_min_bonificada']
		cuota_max_bonificada = row['cuota_max_bonificada']
		base_min = row['base_cotizacion_min']
		base_max = row['base_cotizacion_max']
		
		# Format response
		region_name = {
			"general": "España (territorio común)",
			"ceuta": "Ceuta",
			"melilla": "Melilla"
		}.get(region, region)
		
		formatted_response = f"""✅ **Cuota de Autónomos {year} - {region_name}**

📊 **Tus rendimientos netos**: {ingresos_netos_mensuales}€/mes
📍 **Tramo**: {tramo} de 15

💰 **Cuota mensual**:
- Mínima: {cuota_min:.2f}€
- Máxima: {cuota_max:.2f}€
"""
		
		if bonificacion > 0:
			formatted_response += f"""
🎁 **Bonificación {region_name}**: {bonificacion}% de descuento
- Cuota mínima bonificada: {cuota_min_bonificada:.2f}€
- Cuota máxima bonificada: {cuota_max_bonificada:.2f}€
"""
		
		formatted_response += f"""
📋 **Base de cotización**:
- Mínima: {base_min:.2f}€
- Máxima: {base_max:.2f}€

💡 **¿Qué significa esto?**
- Si cotizas por la **base mínima** ({base_min:.2f}€), pagarás **{cuota_min_bonificada or cuota_min:.2f}€/mes**.
- Puedes elegir cotizar por una base superior (hasta {base_max:.2f}€) para mejorar tus prestaciones futuras.
- Puedes cambiar tu base de cotización hasta **6 veces al año**.

⚠️ **Recuerda**: Esta cuota se calcula sobre tus **rendimientos netos** (ingresos brutos - gastos - deducción del 7%).
"""
		
		return {
			"success": True,
			"tramo": tramo,
			"cuota_minima": cuota_min_bonificada or cuota_min,
			"cuota_maxima": cuota_max_bonificada or cuota_max,
			"bonificacion_percent": bonificacion,
			"region": region,
			"year": year,
			"formatted_response": formatted_response
		}
		
	except Exception as e:
		logger.error(f"Error calculating autonomous quota: {e}", exc_info=True)
		return {
			"success": False,
			"error": str(e),
			"formatted_response": f"❌ Error al calcular la cuota: {str(e)}"
		}