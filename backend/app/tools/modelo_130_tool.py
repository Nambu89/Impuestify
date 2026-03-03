"""
Modelo 130 (Pago Fraccionado IRPF) Calculator Tool for TaxIA

Calculates the quarterly fractional payment of IRPF for self-employed
workers under the direct estimation regime (estimacion directa).

Based on AEAT Disenos de Registro specifications.
Does NOT generate flat files — only computes amounts.

IMPORTANT: All income/expense figures are CUMULATIVE from January 1st
to the end of the quarter being declared.
"""
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Tool definition for OpenAI function calling
MODELO_130_TOOL = {
	"type": "function",
	"function": {
		"name": "calculate_modelo_130",
		"description": """SIEMPRE DEBES USAR ESTA FUNCION cuando el usuario pregunte sobre:
- Modelo 130
- Pago fraccionado de IRPF
- Pago fraccionado trimestral
- Cuanto tengo que pagar de IRPF como autonomo trimestralmente
- Pago a cuenta IRPF autonomos

OBLIGATORIO usar esta funcion si el usuario quiere calcular o simular
su pago fraccionado trimestral de IRPF en estimacion directa.

IMPORTANTE: Los datos del Modelo 130 son ACUMULADOS desde el 1 de enero
hasta el final del trimestre que se declara. Si el usuario da datos de
un solo trimestre, PREGUNTA si son acumulados o del trimestre individual.

La funcion calcula:
- Seccion I: Actividades en estimacion directa (20% del rendimiento neto acumulado)
- Seccion IV: Deduccion art. 80 bis LIRPF (rentas bajas, hasta 100 EUR/trimestre)
- Resultado final a ingresar""",
		"parameters": {
			"type": "object",
			"properties": {
				"trimestre": {
					"type": "integer",
					"description": "Trimestre de la declaracion (1, 2, 3 o 4)"
				},
				"year": {
					"type": "integer",
					"description": "Ano fiscal. Por defecto: ano actual"
				},
				"ingresos_computables": {
					"type": "number",
					"description": "Ingresos ACUMULADOS desde el 1 de enero hasta el final del trimestre (casilla 01). Incluye todos los ingresos de la actividad economica."
				},
				"gastos_deducibles": {
					"type": "number",
					"description": "Gastos deducibles ACUMULADOS desde el 1 de enero hasta el final del trimestre (casilla 02). Incluye gastos necesarios para la actividad."
				},
				"retenciones_ingresos_cuenta": {
					"type": "number",
					"description": "Retenciones e ingresos a cuenta soportados ACUMULADOS (casilla 05). Retenciones que te han practicado clientes. Por defecto: 0"
				},
				"pagos_fraccionados_anteriores": {
					"type": "number",
					"description": "Pagos fraccionados ya ingresados en trimestres previos del MISMO ano (casilla 06). Para T1 siempre es 0. Por defecto: 0"
				},
				"rendimiento_neto_previo_anual": {
					"type": "number",
					"description": "Rendimiento neto de la actividad del ANO ANTERIOR (para calcular deduccion art. 80 bis LIRPF). Si fue <= 12.000 EUR puede haber deduccion. Por defecto: 0 (sin deduccion)"
				}
			},
			"required": ["trimestre", "ingresos_computables", "gastos_deducibles"]
		}
	}
}


async def calculate_modelo_130_tool(
	trimestre: int,
	ingresos_computables: float,
	gastos_deducibles: float,
	year: int = None,
	retenciones_ingresos_cuenta: float = 0,
	pagos_fraccionados_anteriores: float = 0,
	rendimiento_neto_previo_anual: float = 0,
	restricted_mode: bool = False
) -> Dict[str, Any]:
	"""
	Calculate the quarterly fractional IRPF payment (Modelo 130) for
	self-employed workers under direct estimation.

	All income/expense figures must be CUMULATIVE from Jan 1st.

	Args:
		trimestre: Quarter (1-4)
		ingresos_computables: Cumulative income from Jan 1st (casilla 01)
		gastos_deducibles: Cumulative deductible expenses from Jan 1st (casilla 02)
		year: Fiscal year (default: current year)
		retenciones_ingresos_cuenta: Cumulative withholdings suffered (casilla 05)
		pagos_fraccionados_anteriores: Prior quarter payments this year (casilla 06)
		rendimiento_neto_previo_anual: Previous year net income (for art. 80 bis deduction)
		restricted_mode: If True, return restriction message

	Returns:
		Dict with calculation results and formatted response
	"""
	# Safety net: block if restricted (salaried-only plan)
	if restricted_mode:
		from app.security.content_restriction import get_autonomo_block_response
		logger.warning("calculate_modelo_130 called in restricted_mode — blocking")
		return {
			"success": False,
			"error": "restricted",
			"formatted_response": get_autonomo_block_response()
		}

	try:
		# Default year
		if year is None:
			year = datetime.now().year

		# Validate trimestre
		if trimestre not in (1, 2, 3, 4):
			return {
				"success": False,
				"error": "Trimestre debe ser 1, 2, 3 o 4",
				"formatted_response": "El trimestre debe ser 1, 2, 3 o 4."
			}

		# Ensure non-negative inputs where applicable
		retenciones_ingresos_cuenta = max(retenciones_ingresos_cuenta, 0)
		pagos_fraccionados_anteriores = max(pagos_fraccionados_anteriores, 0)

		# ===== SECCION I: Actividades en Estimacion Directa =====
		casilla_01 = ingresos_computables
		casilla_02 = gastos_deducibles
		casilla_03 = max(casilla_01 - casilla_02, 0)  # Rendimiento neto (floor 0)
		casilla_04 = round(casilla_03 * 0.20, 2)       # 20% del rendimiento neto
		casilla_05 = retenciones_ingresos_cuenta
		casilla_06 = pagos_fraccionados_anteriores
		casilla_07 = max(round(casilla_04 - casilla_05 - casilla_06, 2), 0)  # Resultado seccion I

		# ===== SECCION IV: Deduccion art. 80 bis LIRPF (rentas bajas) =====
		deduccion_80bis = 0.0
		deduccion_aplicable = False

		if rendimiento_neto_previo_anual > 0 and rendimiento_neto_previo_anual <= 12000:
			deduccion_aplicable = True
			rn = rendimiento_neto_previo_anual

			if rn <= 9000:
				deduccion_80bis = 100.0
			elif rn <= 10000:
				deduccion_80bis = 100.0 - (rn - 9000) * 0.075
			elif rn <= 11000:
				deduccion_80bis = 25.0 - (rn - 10000) * 0.0125
			elif rn <= 12000:
				deduccion_80bis = 12.5 - (rn - 11000) * 0.0125

			deduccion_80bis = max(round(deduccion_80bis, 2), 0)

		# ===== RESULTADO FINAL =====
		resultado_final = max(round(casilla_07 - deduccion_80bis, 2), 0)

		# Quarter label
		trimestre_label = {1: "1T", 2: "2T", 3: "3T", 4: "4T"}[trimestre]
		trimestre_meses = {
			1: "enero-marzo",
			2: "abril-junio",
			3: "julio-septiembre",
			4: "octubre-diciembre"
		}[trimestre]
		acumulado_desde = {
			1: "enero a marzo",
			2: "enero a junio",
			3: "enero a septiembre",
			4: "enero a diciembre"
		}[trimestre]

		# Build formatted response
		lines = []
		lines.append(f"**Modelo 130 — {trimestre_label} {year} ({trimestre_meses})**")
		lines.append("")
		lines.append(f"Datos acumulados de {acumulado_desde} {year}:")
		lines.append("")

		# Seccion I
		lines.append("**Seccion I: Actividades en estimacion directa**")
		lines.append(f"- Ingresos computables [01]: {casilla_01:,.2f} EUR")
		lines.append(f"- Gastos deducibles [02]: {casilla_02:,.2f} EUR")
		lines.append(f"- Rendimiento neto [03]: {casilla_03:,.2f} EUR")
		lines.append(f"- 20% del rendimiento [04]: {casilla_04:,.2f} EUR")

		if casilla_05 > 0:
			lines.append(f"- Retenciones e ingresos a cuenta [05]: -{casilla_05:,.2f} EUR")
		if casilla_06 > 0:
			lines.append(f"- Pagos fraccionados anteriores [06]: -{casilla_06:,.2f} EUR")

		lines.append(f"- **Resultado seccion I [07]: {casilla_07:,.2f} EUR**")
		lines.append("")

		# Seccion IV (deduccion 80 bis)
		if deduccion_aplicable:
			lines.append("**Seccion IV: Deduccion art. 80 bis LIRPF**")
			lines.append(f"- Rendimiento neto ano anterior: {rendimiento_neto_previo_anual:,.2f} EUR")
			lines.append(f"- Deduccion trimestral: {deduccion_80bis:,.2f} EUR")
			lines.append("")

		# Resultado final
		lines.append("**Resultado**")
		if resultado_final > 0:
			lines.append(f"- 💰 **A ingresar: {resultado_final:,.2f} EUR**")
		else:
			lines.append(f"- 0️⃣ **Resultado: {resultado_final:,.2f} EUR (sin ingreso)**")

		# Explanatory notes
		lines.append("")
		if resultado_final > 0:
			lines.append(f"Debes ingresar {resultado_final:,.2f} EUR a Hacienda antes del dia 20 del mes siguiente al trimestre (o 30 de enero para el 4T).")
		else:
			lines.append("No tienes que ingresar nada este trimestre, pero debes presentar el modelo igualmente (con resultado 0).")

		# Reminder about cumulative nature
		lines.append("")
		lines.append(f"Los importes son **acumulados** desde el 1 de enero hasta el {trimestre_meses.split('-')[1]} de {year}. ")
		if trimestre > 1:
			lines.append(f"Los pagos fraccionados de trimestres anteriores ({casilla_06:,.2f} EUR) ya se descuentan del calculo.")

		lines.append("")
		lines.append("Este calculo corresponde a la **estimacion directa** (normal o simplificada). No cubre estimacion objetiva (modulos, Modelo 131).")

		formatted_response = "\n".join(lines)

		logger.info(
			f"Modelo 130 calculated: {trimestre_label} {year}, "
			f"ingresos={casilla_01}, gastos={casilla_02}, "
			f"neto={casilla_03}, resultado={resultado_final}"
		)

		return {
			"success": True,
			"trimestre": trimestre,
			"year": year,
			"seccion_i": {
				"ingresos_computables": casilla_01,
				"gastos_deducibles": casilla_02,
				"rendimiento_neto": casilla_03,
				"veinte_porciento": casilla_04,
				"retenciones": casilla_05,
				"pagos_anteriores": casilla_06,
				"resultado_seccion": casilla_07
			},
			"deduccion_80bis": deduccion_80bis,
			"resultado_final": resultado_final,
			"formatted_response": formatted_response
		}

	except Exception as e:
		logger.error(f"Error calculating Modelo 130: {e}", exc_info=True)
		return {
			"success": False,
			"error": str(e),
			"formatted_response": f"Error al calcular el Modelo 130: {str(e)}"
		}
