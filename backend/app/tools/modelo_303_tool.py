"""
Modelo 303 (IVA Trimestral) Calculator Tool for TaxIA

Calculates the main fields of the quarterly VAT return (Modelo 303)
for self-employed / businesses under the general regime (regimen general).

Based on AEAT Disenos de Registro specifications.
Does NOT generate flat files — only computes amounts.
"""
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Tool definition for OpenAI function calling
MODELO_303_TOOL = {
	"type": "function",
	"function": {
		"name": "calculate_modelo_303",
		"description": """SIEMPRE DEBES USAR ESTA FUNCION cuando el usuario pregunte sobre:
- Modelo 303
- Declaracion trimestral de IVA
- IVA trimestral
- Liquidacion de IVA
- Cuanto IVA tengo que pagar este trimestre
- IVA devengado / IVA deducible / IVA repercutido / IVA soportado

OBLIGATORIO usar esta funcion si el usuario quiere calcular o simular el resultado
de su declaracion trimestral de IVA (regimen general).

La funcion calcula las casillas principales del Modelo 303:
- IVA devengado (repercutido) por tipos: 21%, 10%, 4%
- IVA deducible (soportado) en compras
- Resultado: a ingresar, a compensar o a devolver
- Adquisiciones intracomunitarias
- Compensacion de periodos anteriores""",
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
				"base_21": {
					"type": "number",
					"description": "Base imponible de operaciones al 21% de IVA (ventas/servicios al tipo general)"
				},
				"base_10": {
					"type": "number",
					"description": "Base imponible de operaciones al 10% de IVA (tipo reducido). Por defecto: 0"
				},
				"base_4": {
					"type": "number",
					"description": "Base imponible de operaciones al 4% de IVA (tipo superreducido). Por defecto: 0"
				},
				"base_adquisiciones_intra": {
					"type": "number",
					"description": "Base imponible de adquisiciones intracomunitarias. Por defecto: 0"
				},
				"tipo_adquisiciones_intra": {
					"type": "number",
					"description": "Tipo de IVA aplicable a adquisiciones intracomunitarias (%). Por defecto: 21"
				},
				"iva_deducible_bienes_corrientes": {
					"type": "number",
					"description": "IVA soportado deducible en compras de bienes y servicios corrientes (casilla 29)"
				},
				"base_deducible_bienes_corrientes": {
					"type": "number",
					"description": "Base imponible de las compras deducibles de bienes corrientes (casilla 28, informativo). Por defecto: 0"
				},
				"iva_deducible_bienes_inversion": {
					"type": "number",
					"description": "IVA soportado deducible en bienes de inversion (casilla 31). Por defecto: 0"
				},
				"iva_deducible_importaciones": {
					"type": "number",
					"description": "IVA soportado deducible en importaciones (casilla 33). Por defecto: 0"
				},
				"iva_deducible_intracomunitarias": {
					"type": "number",
					"description": "IVA soportado deducible en adquisiciones intracomunitarias (casilla 37). Por defecto: 0"
				},
				"rectificacion_deducciones": {
					"type": "number",
					"description": "Rectificacion de deducciones, puede ser positivo o negativo (casilla 41). Por defecto: 0"
				},
				"compensacion_periodos_anteriores": {
					"type": "number",
					"description": "Cuotas a compensar de periodos anteriores (casilla 71, siempre >= 0). Por defecto: 0"
				},
				"porcentaje_atribucion_estado": {
					"type": "number",
					"description": "Porcentaje de IVA atribuible al Estado, para empresas con actividad en territorios forales (casilla 65). Por defecto: 100"
				}
			},
			"required": ["trimestre", "base_21", "iva_deducible_bienes_corrientes"]
		}
	}
}


async def calculate_modelo_303_tool(
	trimestre: int,
	base_21: float,
	iva_deducible_bienes_corrientes: float,
	year: int = None,
	base_10: float = 0,
	base_4: float = 0,
	base_adquisiciones_intra: float = 0,
	tipo_adquisiciones_intra: float = 21,
	base_deducible_bienes_corrientes: float = 0,
	iva_deducible_bienes_inversion: float = 0,
	iva_deducible_importaciones: float = 0,
	iva_deducible_intracomunitarias: float = 0,
	rectificacion_deducciones: float = 0,
	compensacion_periodos_anteriores: float = 0,
	porcentaje_atribucion_estado: float = 100,
	restricted_mode: bool = False
) -> Dict[str, Any]:
	"""
	Calculate the quarterly VAT return (Modelo 303) under the general regime.

	Args:
		trimestre: Quarter (1-4)
		base_21: Tax base for 21% VAT operations
		iva_deducible_bienes_corrientes: Deductible input VAT on current goods/services
		year: Fiscal year (default: current year)
		base_10: Tax base for 10% VAT operations
		base_4: Tax base for 4% VAT operations
		base_adquisiciones_intra: Tax base for intra-community acquisitions
		tipo_adquisiciones_intra: VAT rate for intra-community acquisitions
		base_deducible_bienes_corrientes: Tax base for deductible current goods (informational)
		iva_deducible_bienes_inversion: Deductible input VAT on investment goods
		iva_deducible_importaciones: Deductible input VAT on imports
		iva_deducible_intracomunitarias: Deductible input VAT on intra-community acquisitions
		rectificacion_deducciones: Adjustment to deductions (+/-)
		compensacion_periodos_anteriores: Amounts to offset from prior periods
		porcentaje_atribucion_estado: % attributable to state (for foral territories)
		restricted_mode: If True, return restriction message

	Returns:
		Dict with calculation results and formatted response
	"""
	# Safety net: block if restricted (salaried-only plan)
	if restricted_mode:
		from app.security.content_restriction import get_autonomo_block_response
		logger.warning("calculate_modelo_303 called in restricted_mode — blocking")
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

		# Validate porcentaje
		if not (0 < porcentaje_atribucion_estado <= 100):
			return {
				"success": False,
				"error": "El porcentaje de atribucion al Estado debe estar entre 0 y 100",
				"formatted_response": "El porcentaje de atribucion al Estado debe estar entre 0 y 100."
			}

		# Ensure compensacion is non-negative
		compensacion_periodos_anteriores = max(compensacion_periodos_anteriores, 0)

		# ===== IVA DEVENGADO (output VAT) =====
		casilla_01 = base_21
		casilla_03 = round(base_21 * 0.21, 2)

		casilla_04 = base_10
		casilla_06 = round(base_10 * 0.10, 2)

		casilla_07 = base_4
		casilla_09 = round(base_4 * 0.04, 2)

		# Adquisiciones intracomunitarias
		casilla_10 = base_adquisiciones_intra
		casilla_12 = round(base_adquisiciones_intra * (tipo_adquisiciones_intra / 100), 2)

		# Total IVA devengado
		casilla_27 = round(casilla_03 + casilla_06 + casilla_09 + casilla_12, 2)

		# ===== IVA DEDUCIBLE (input VAT) =====
		casilla_28 = base_deducible_bienes_corrientes
		casilla_29 = iva_deducible_bienes_corrientes
		casilla_31 = iva_deducible_bienes_inversion
		casilla_33 = iva_deducible_importaciones
		casilla_37 = iva_deducible_intracomunitarias
		casilla_41 = rectificacion_deducciones

		# Total a deducir
		casilla_45 = round(
			casilla_29 + casilla_31 + casilla_33 + casilla_37 + casilla_41,
			2
		)

		# ===== RESULTADO =====
		casilla_46 = round(casilla_27 - casilla_45, 2)  # Resultado regimen general

		# Suma de resultados (without other regimes, equals casilla_46)
		casilla_64 = casilla_46

		# Atribucion al Estado
		casilla_65 = porcentaje_atribucion_estado
		casilla_66 = round(casilla_64 * (porcentaje_atribucion_estado / 100), 2)

		# Resultado previo (without pro-rata or other adjustments)
		casilla_69 = casilla_66

		# Compensacion periodos anteriores
		casilla_71 = compensacion_periodos_anteriores

		# Resultado final
		resultado_final = round(casilla_69 - casilla_71, 2)

		# Determine result type
		if resultado_final > 0:
			tipo_resultado = "A ingresar"
			emoji_resultado = "💰"
		elif resultado_final < 0:
			if trimestre == 4:
				tipo_resultado = "A devolver"
				emoji_resultado = "🔄"
			else:
				tipo_resultado = "A compensar"
				emoji_resultado = "➡️"
		else:
			tipo_resultado = "Sin actividad"
			emoji_resultado = "0️⃣"

		# Quarter label
		trimestre_label = {1: "1T", 2: "2T", 3: "3T", 4: "4T"}[trimestre]
		trimestre_meses = {
			1: "enero-marzo",
			2: "abril-junio",
			3: "julio-septiembre",
			4: "octubre-diciembre"
		}[trimestre]

		# Build formatted response
		lines = []
		lines.append(f"**Modelo 303 — {trimestre_label} {year} ({trimestre_meses})**")
		lines.append("")

		# IVA Devengado section
		lines.append("**IVA Devengado (repercutido)**")
		if base_21 > 0:
			lines.append(f"- Base 21%: {base_21:,.2f} EUR | Cuota: {casilla_03:,.2f} EUR")
		if base_10 > 0:
			lines.append(f"- Base 10%: {base_10:,.2f} EUR | Cuota: {casilla_06:,.2f} EUR")
		if base_4 > 0:
			lines.append(f"- Base 4%: {base_4:,.2f} EUR | Cuota: {casilla_09:,.2f} EUR")
		if base_adquisiciones_intra > 0:
			lines.append(f"- Adquisiciones intracomunitarias: {base_adquisiciones_intra:,.2f} EUR al {tipo_adquisiciones_intra}% | Cuota: {casilla_12:,.2f} EUR")
		lines.append(f"- **Total devengado [27]: {casilla_27:,.2f} EUR**")
		lines.append("")

		# IVA Deducible section
		lines.append("**IVA Deducible (soportado)**")
		if casilla_29 > 0:
			base_info = f" (base: {casilla_28:,.2f} EUR)" if casilla_28 > 0 else ""
			lines.append(f"- Bienes y servicios corrientes [29]: {casilla_29:,.2f} EUR{base_info}")
		if casilla_31 > 0:
			lines.append(f"- Bienes de inversion [31]: {casilla_31:,.2f} EUR")
		if casilla_33 > 0:
			lines.append(f"- Importaciones [33]: {casilla_33:,.2f} EUR")
		if casilla_37 > 0:
			lines.append(f"- Adquisiciones intracomunitarias [37]: {casilla_37:,.2f} EUR")
		if casilla_41 != 0:
			signo = "+" if casilla_41 > 0 else ""
			lines.append(f"- Rectificacion deducciones [41]: {signo}{casilla_41:,.2f} EUR")
		lines.append(f"- **Total a deducir [45]: {casilla_45:,.2f} EUR**")
		lines.append("")

		# Resultado
		lines.append("**Resultado**")
		lines.append(f"- Resultado regimen general [46]: {casilla_46:,.2f} EUR")
		if porcentaje_atribucion_estado < 100:
			lines.append(f"- Atribucion al Estado ({porcentaje_atribucion_estado}%) [66]: {casilla_66:,.2f} EUR")
		if compensacion_periodos_anteriores > 0:
			lines.append(f"- Compensacion periodos anteriores [71]: -{casilla_71:,.2f} EUR")
		lines.append(f"- {emoji_resultado} **Resultado final: {resultado_final:,.2f} EUR — {tipo_resultado}**")

		# Explanatory note
		lines.append("")
		if resultado_final > 0:
			lines.append(f"Debes ingresar {resultado_final:,.2f} EUR a Hacienda antes del dia 20 del mes siguiente al trimestre (o 30 de enero para el 4T).")
		elif resultado_final < 0 and trimestre < 4:
			lines.append(f"El resultado negativo de {abs(resultado_final):,.2f} EUR se compensa en el siguiente trimestre (casilla 71 del proximo 303).")
		elif resultado_final < 0 and trimestre == 4:
			lines.append(f"En el 4T puedes solicitar la devolucion de {abs(resultado_final):,.2f} EUR o compensar en el siguiente ejercicio.")

		lines.append("")
		lines.append("Este calculo cubre solo el **regimen general** de IVA. No incluye regimenes especiales (simplificado, recargo de equivalencia, agricultura, bienes usados, etc.).")

		formatted_response = "\n".join(lines)

		logger.info(
			f"Modelo 303 calculated: {trimestre_label} {year}, "
			f"devengado={casilla_27}, deducible={casilla_45}, "
			f"resultado={resultado_final} ({tipo_resultado})"
		)

		return {
			"success": True,
			"trimestre": trimestre,
			"year": year,
			"iva_devengado": {
				"cuota_21": casilla_03,
				"cuota_10": casilla_06,
				"cuota_4": casilla_09,
				"cuota_intracomunitaria": casilla_12,
				"total_devengado": casilla_27
			},
			"iva_deducible": {
				"bienes_corrientes": casilla_29,
				"bienes_inversion": casilla_31,
				"importaciones": casilla_33,
				"intracomunitarias": casilla_37,
				"rectificacion": casilla_41,
				"total_deducible": casilla_45
			},
			"resultado": {
				"regimen_general": casilla_46,
				"atribucion_estado": casilla_66,
				"compensacion_anterior": casilla_71,
				"resultado_final": resultado_final,
				"tipo": tipo_resultado
			},
			"formatted_response": formatted_response
		}

	except Exception as e:
		logger.error(f"Error calculating Modelo 303: {e}", exc_info=True)
		return {
			"success": False,
			"error": str(e),
			"formatted_response": f"Error al calcular el Modelo 303: {str(e)}"
		}
