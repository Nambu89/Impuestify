"""
Modelo 303 (IVA Trimestral) Calculator Tool for TaxIA

Calculates the main fields of the quarterly VAT return (Modelo 303)
for self-employed / businesses under the general regime (regimen general).

CCAA-aware: automatically routes Canarias to IGIC/Modelo 420, redirects
Ceuta/Melilla to calculate_modelo_ipsi, and annotates foral territories
(Gipuzkoa → Mod.300, Navarra → F69, Bizkaia/Araba → Mod.303 foral + TicketBAI).

Based on AEAT Disenos de Registro specifications.
Does NOT generate flat files — only computes amounts.
"""
from typing import Dict, Any
from datetime import datetime
import logging

from app.utils.ccaa_constants import normalize_ccaa, FORAL_VASCO, CEUTA_MELILLA, CANARIAS_SET

logger = logging.getLogger(__name__)

# Foral territories that still use IVA but with a different model/hacienda
_FORAL_IVA_CONFIG: dict[str, dict] = {
    "Gipuzkoa": {
        "modelo": "300",
        "impuesto": "IVA",
        "tipo_general": 0.21,
        "donde_presentar": "Hacienda Foral de Gipuzkoa (gipuzkoa.eus)",
        "nota_extra": "TicketBAI obligatorio para todas las facturas desde 2022.",
    },
    "Navarra": {
        "modelo": "F69",
        "impuesto": "IVA",
        "tipo_general": 0.21,
        "donde_presentar": "Hacienda Foral de Navarra (hacienda.navarra.es)",
        "nota_extra": None,
    },
    "Bizkaia": {
        "modelo": "303 (foral)",
        "impuesto": "IVA",
        "tipo_general": 0.21,
        "donde_presentar": "Hacienda Foral de Bizkaia (bizkaia.eus)",
        "nota_extra": "TicketBAI + BATUZ obligatorio (envio continuo de facturas).",
    },
    "Araba": {
        "modelo": "303 (foral)",
        "impuesto": "IVA",
        "tipo_general": 0.21,
        "donde_presentar": "Hacienda Foral de Araba (araba.eus)",
        "nota_extra": "TicketBAI obligatorio para todas las facturas.",
    },
}

# Tool definition for OpenAI function calling
MODELO_303_TOOL = {
	"type": "function",
	"function": {
		"name": "calculate_modelo_303",
		"description": """SIEMPRE DEBES USAR ESTA FUNCION cuando el usuario pregunte sobre:
- Modelo 303 / Modelo 300 / Modelo F69 / Modelo 420
- Declaracion trimestral de IVA o IGIC
- IVA trimestral / IGIC trimestral
- Liquidacion de IVA o IGIC
- Cuanto IVA o IGIC tengo que pagar este trimestre
- IVA devengado / IVA deducible / IVA repercutido / IVA soportado

OBLIGATORIO usar esta funcion si el usuario quiere calcular o simular el resultado
de su declaracion trimestral de IVA o IGIC (regimen general).

PASA SIEMPRE la ccaa del usuario. La funcion se adapta automaticamente:
- Canarias → calcula IGIC al 7% (Modelo 420, Gobierno de Canarias)
- Gipuzkoa → Modelo 300 con TicketBAI
- Navarra → Modelo F69 (Hacienda Foral de Navarra)
- Bizkaia → Modelo 303 foral + BATUZ/TicketBAI
- Araba → Modelo 303 foral + TicketBAI
- Ceuta/Melilla → redirige a calculate_modelo_ipsi (IPSI, no IVA)
- Resto (regimen comun) → Modelo 303 AEAT, tipos 21%/10%/4%

La funcion calcula las casillas principales del modelo correspondiente:
- Cuota devengada (repercutida) por tipos
- Cuota deducible (soportada) en compras
- Resultado: a ingresar, a compensar o a devolver
- Adquisiciones intracomunitarias o extracanarias
- Compensacion de periodos anteriores""",
		"parameters": {
			"type": "object",
			"properties": {
				"trimestre": {
					"type": "integer",
					"description": "Trimestre de la declaracion (1, 2, 3 o 4)"
				},
				"ccaa": {
					"type": "string",
					"description": "CCAA o territorio del usuario. Ejemplos: 'Madrid', 'Canarias', 'Gipuzkoa', 'Navarra', 'Bizkaia', 'Araba', 'Ceuta', 'Melilla'. Si no se indica, se asume regimen comun (Modelo 303 AEAT)."
				},
				"year": {
					"type": "integer",
					"description": "Ano fiscal. Por defecto: ano actual"
				},
				"base_21": {
					"type": "number",
					"description": "Base imponible de operaciones al tipo general (21% IVA en regimen comun; 7% IGIC en Canarias). Para Canarias este campo se usa como base al tipo general IGIC (7%)."
				},
				"base_10": {
					"type": "number",
					"description": "Base imponible de operaciones al 10% de IVA (tipo reducido, regimen comun). Para Canarias usar base_igic_3 en su lugar. Por defecto: 0"
				},
				"base_4": {
					"type": "number",
					"description": "Base imponible de operaciones al 4% de IVA (tipo superreducido, regimen comun). Por defecto: 0"
				},
				"base_adquisiciones_intra": {
					"type": "number",
					"description": "Base imponible de adquisiciones intracomunitarias (regimen comun) o extracanarias (Canarias). Por defecto: 0"
				},
				"tipo_adquisiciones_intra": {
					"type": "number",
					"description": "Tipo de IVA/IGIC aplicable a adquisiciones intracomunitarias/extracanarias (%). Por defecto: 21 en regimen comun, 7 en Canarias"
				},
				"iva_deducible_bienes_corrientes": {
					"type": "number",
					"description": "IVA/IGIC soportado deducible en compras de bienes y servicios corrientes (casilla 29 en Mod.303 / cuota corrientes en Mod.420)"
				},
				"base_deducible_bienes_corrientes": {
					"type": "number",
					"description": "Base imponible de las compras deducibles de bienes corrientes (informativo). Por defecto: 0"
				},
				"iva_deducible_bienes_inversion": {
					"type": "number",
					"description": "IVA/IGIC soportado deducible en bienes de inversion. Por defecto: 0"
				},
				"iva_deducible_importaciones": {
					"type": "number",
					"description": "IVA/IGIC soportado deducible en importaciones. Por defecto: 0"
				},
				"iva_deducible_intracomunitarias": {
					"type": "number",
					"description": "IVA soportado deducible en adquisiciones intracomunitarias (casilla 37, solo regimen comun). Por defecto: 0"
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
	ccaa: str = None,
	year: int = None,
	base_10: float = 0,
	base_4: float = 0,
	base_adquisiciones_intra: float = 0,
	tipo_adquisiciones_intra: float = None,
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
	Calculate the quarterly VAT/IGIC return, routing by CCAA:
	  - Canarias        → IGIC Modelo 420 (7% tipo general)
	  - Ceuta / Melilla → redirect hint to calculate_modelo_ipsi
	  - Gipuzkoa        → IVA Modelo 300, TicketBAI
	  - Navarra          → IVA Modelo F69
	  - Bizkaia          → IVA Modelo 303 foral + BATUZ/TicketBAI
	  - Araba            → IVA Modelo 303 foral + TicketBAI
	  - Resto            → IVA Modelo 303 AEAT (comportamiento anterior intacto)

	Args:
		trimestre: Quarter (1-4)
		base_21: Tax base at general rate (21% IVA or 7% IGIC for Canarias)
		iva_deducible_bienes_corrientes: Deductible input tax on current goods/services
		ccaa: CCAA or territory of the user (optional; defaults to regimen comun)
		year: Fiscal year (default: current year)
		base_10: Tax base for 10% VAT (regimen comun only)
		base_4: Tax base for 4% VAT (regimen comun only)
		base_adquisiciones_intra: Tax base for intra-community / extra-canarian acquisitions
		tipo_adquisiciones_intra: Rate for intra-community acquisitions (%; defaults 21 or 7)
		base_deducible_bienes_corrientes: Tax base for deductible current goods (informational)
		iva_deducible_bienes_inversion: Deductible input tax on investment goods
		iva_deducible_importaciones: Deductible input tax on imports
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

		# ===== CCAA ROUTING =====
		ccaa_canonical = normalize_ccaa(ccaa) if ccaa else None

		# --- Ceuta / Melilla: redirect to IPSI tool ---
		if ccaa_canonical in CEUTA_MELILLA:
			msg = (
				f"En {ccaa_canonical} no se aplica IVA sino IPSI "
				f"(Impuesto sobre la Produccion, los Servicios y la Importacion). "
				f"Usa la funcion calculate_modelo_ipsi para calcular tu autoliquidacion trimestral. "
				f"Los tipos IPSI son: 0,5% / 1% / 2% / 4% (general) / 8% / 10%."
			)
			return {
				"success": False,
				"redirect": "calculate_modelo_ipsi",
				"ccaa": ccaa_canonical,
				"modelo": "IPSI",
				"impuesto": "IPSI",
				"donde_presentar": f"Ciudad Autonoma de {ccaa_canonical}",
				"formatted_response": msg,
			}

		# --- Canarias: IGIC via Modelo 420 ---
		if ccaa_canonical in CANARIAS_SET:
			return await _calculate_igic_420(
				trimestre=trimestre,
				year=year,
				base_7=base_21,  # caller passes general-rate base as base_21
				base_3=base_10,  # tipo reducido IGIC 3%
				base_extracanarias=base_adquisiciones_intra,
				tipo_extracanarias=(tipo_adquisiciones_intra / 100) if tipo_adquisiciones_intra is not None else 0.07,
				cuota_corrientes=iva_deducible_bienes_corrientes,
				cuota_inversion=iva_deducible_bienes_inversion,
				cuota_importaciones=iva_deducible_importaciones,
				rectificacion=rectificacion_deducciones,
				compensacion=compensacion_periodos_anteriores,
			)

		# --- Foral IVA territories (Gipuzkoa, Navarra, Bizkaia, Araba) ---
		if ccaa_canonical in _FORAL_IVA_CONFIG:
			foral_cfg = _FORAL_IVA_CONFIG[ccaa_canonical]
			# Fall through to the standard IVA calculation below, but annotate the output
			foral_override = foral_cfg
		else:
			foral_override = None

		# Default tipo_adquisiciones_intra for IVA regimen comun
		if tipo_adquisiciones_intra is None:
			tipo_adquisiciones_intra = 21

		# ===== IVA DEVENGADO (output VAT) — regimen comun + foral IVA =====
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

		# Determine model/hacienda from foral config or regimen comun defaults
		if foral_override:
			modelo_label = foral_override["modelo"]
			donde_presentar = foral_override["donde_presentar"]
			nota_territorial = foral_override.get("nota_extra") or ""
		else:
			modelo_label = "303"
			donde_presentar = "AEAT (sede.agenciatributaria.gob.es)"
			nota_territorial = ""

		# Build formatted response
		lines = []
		lines.append(f"**Modelo {modelo_label} — {trimestre_label} {year} ({trimestre_meses})**")
		if foral_override or ccaa_canonical:
			lines.append(f"Presentacion: {donde_presentar}")
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
		if nota_territorial:
			lines.append(f"\nNota territorial: {nota_territorial}")

		formatted_response = "\n".join(lines)

		logger.info(
			f"Modelo {modelo_label} calculated: ccaa={ccaa_canonical}, {trimestre_label} {year}, "
			f"devengado={casilla_27}, deducible={casilla_45}, "
			f"resultado={resultado_final} ({tipo_resultado})"
		)

		return {
			"success": True,
			"trimestre": trimestre,
			"year": year,
			"ccaa": ccaa_canonical,
			"modelo": modelo_label,
			"impuesto": "IVA",
			"tipo_aplicado": 21,
			"donde_presentar": donde_presentar,
			"notas": nota_territorial or None,
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


async def _calculate_igic_420(
	trimestre: int,
	year: int,
	base_7: float,
	base_3: float,
	base_extracanarias: float,
	tipo_extracanarias: float,
	cuota_corrientes: float,
	cuota_inversion: float,
	cuota_importaciones: float,
	rectificacion: float,
	compensacion: float,
) -> Dict[str, Any]:
	"""
	Delegate Canarias IGIC calculation to the existing Modelo420Calculator.

	Maps the simplified IVA-style input params from calculate_modelo_303
	to Modelo420Calculator's full interface.
	"""
	from app.utils.calculators.modelo_420 import Modelo420Calculator

	calc = Modelo420Calculator(None)
	result = await calc.calculate(
		base_3=base_3,
		base_7=base_7,
		base_extracanarias=base_extracanarias,
		tipo_extracanarias=tipo_extracanarias,
		cuota_corrientes_interiores=cuota_corrientes,
		cuota_inversion_interiores=cuota_inversion,
		cuota_importaciones_corrientes=cuota_importaciones,
		rectificacion_deducciones=rectificacion,
		cuotas_compensar_anteriores=compensacion,
		quarter=trimestre,
	)

	total_devengado = result["total_devengado"]
	total_deducible = result["total_deducible"]
	resultado = result["resultado_liquidacion"]

	trimestre_label = {1: "1T", 2: "2T", 3: "3T", 4: "4T"}[trimestre]
	trimestre_meses = {
		1: "enero-marzo",
		2: "abril-junio",
		3: "julio-septiembre",
		4: "octubre-diciembre",
	}[trimestre]

	if resultado > 0:
		tipo_resultado = "A ingresar"
	elif resultado < 0:
		tipo_resultado = "A devolver" if trimestre == 4 else "A compensar"
	else:
		tipo_resultado = "Sin actividad"

	lines = []
	lines.append(f"**Modelo 420 (IGIC) — Canarias — {trimestre_label} {year} ({trimestre_meses})**")
	lines.append("Presentacion: Gobierno de Canarias (sede.gobiernodecanarias.org)")
	lines.append("")
	lines.append("**IGIC Devengado (repercutido)**")
	dsg = result["desglose_devengado"]
	if dsg["tipo_reducido"]["base"] > 0:
		lines.append(f"- Base 3% (reducido): {dsg['tipo_reducido']['base']:,.2f} EUR | Cuota: {dsg['tipo_reducido']['cuota']:,.2f} EUR")
	if dsg["tipo_general"]["base"] > 0:
		lines.append(f"- Base 7% (general): {dsg['tipo_general']['base']:,.2f} EUR | Cuota: {dsg['tipo_general']['cuota']:,.2f} EUR")
	if dsg["adquisiciones_extracanarias"]["base"] > 0:
		lines.append(
			f"- Adquisiciones extracanarias: {dsg['adquisiciones_extracanarias']['base']:,.2f} EUR "
			f"al {dsg['adquisiciones_extracanarias']['tipo']*100:.1f}% | "
			f"Cuota: {dsg['adquisiciones_extracanarias']['cuota']:,.2f} EUR"
		)
	lines.append(f"- **Total devengado: {total_devengado:,.2f} EUR**")
	lines.append("")
	lines.append("**IGIC Deducible (soportado)**")
	ddc = result["desglose_deducible"]
	if ddc["cuota_corrientes_interiores"] > 0:
		lines.append(f"- Bienes y servicios corrientes: {ddc['cuota_corrientes_interiores']:,.2f} EUR")
	if ddc["cuota_inversion_interiores"] > 0:
		lines.append(f"- Bienes de inversion: {ddc['cuota_inversion_interiores']:,.2f} EUR")
	if ddc["cuota_importaciones_corrientes"] > 0:
		lines.append(f"- Importaciones: {ddc['cuota_importaciones_corrientes']:,.2f} EUR")
	if ddc["rectificacion_deducciones"] != 0:
		signo = "+" if ddc["rectificacion_deducciones"] > 0 else ""
		lines.append(f"- Rectificacion deducciones: {signo}{ddc['rectificacion_deducciones']:,.2f} EUR")
	lines.append(f"- **Total a deducir: {total_deducible:,.2f} EUR**")
	lines.append("")
	lines.append("**Resultado**")
	lines.append(f"- Resultado regimen general: {result['resultado_regimen_general']:,.2f} EUR")
	if compensacion > 0:
		lines.append(f"- Compensacion periodos anteriores: -{result['cuotas_compensar_anteriores']:,.2f} EUR")
	lines.append(f"- **Resultado final: {resultado:,.2f} EUR — {tipo_resultado}**")
	lines.append("")
	if resultado > 0:
		lines.append(
			f"Debes ingresar {resultado:,.2f} EUR al Gobierno de Canarias antes del dia 20 del mes "
			f"siguiente al trimestre (o 30 de enero para el 4T)."
		)
	elif resultado < 0 and trimestre < 4:
		lines.append(
			f"El resultado negativo de {abs(resultado):,.2f} EUR se compensa en el siguiente trimestre "
			f"(cuotas a compensar del proximo Modelo 420)."
		)
	elif resultado < 0 and trimestre == 4:
		lines.append(f"En el 4T puedes solicitar la devolucion de {abs(resultado):,.2f} EUR o compensar.")
	lines.append("")
	lines.append(
		"IGIC = Impuesto General Indirecto Canario. Canarias NO pertenece al territorio IVA armonizado de la UE "
		"(Art. 6 Directiva IVA). El Modelo 349 (operaciones intracomunitarias) NO aplica desde Canarias: "
		"las facturas a Google Ireland, Meta Ireland, etc. son EXPORTACION de servicios, no operacion intracomunitaria."
	)
	lines.append("Este calculo cubre solo el **regimen general** del IGIC. No incluye regimenes especiales.")

	logger.info(
		f"Modelo 420 (IGIC) Canarias calculated: {trimestre_label} {year}, "
		f"devengado={total_devengado}, deducible={total_deducible}, resultado={resultado} ({tipo_resultado})"
	)

	return {
		"success": True,
		"trimestre": trimestre,
		"year": year,
		"ccaa": "Canarias",
		"modelo": "420",
		"impuesto": "IGIC",
		"tipo_aplicado": 7,
		"donde_presentar": "Gobierno de Canarias (sede.gobiernodecanarias.org)",
		"notas": (
			"Canarias no pertenece al territorio IVA armonizado de la UE. "
			"El Modelo 349 NO aplica desde Canarias. "
			"Facturas a plataformas extranjeras (Google, Meta, etc.) = exportacion de servicios."
		),
		"igic_devengado": {
			"cuota_3": dsg["tipo_reducido"]["cuota"],
			"cuota_7": dsg["tipo_general"]["cuota"],
			"cuota_extracanarias": dsg["adquisiciones_extracanarias"]["cuota"],
			"total_devengado": total_devengado,
		},
		"igic_deducible": {
			"bienes_corrientes": ddc["cuota_corrientes_interiores"],
			"bienes_inversion": ddc["cuota_inversion_interiores"],
			"importaciones": ddc["cuota_importaciones_corrientes"],
			"rectificacion": ddc["rectificacion_deducciones"],
			"total_deducible": total_deducible,
		},
		"resultado": {
			"regimen_general": result["resultado_regimen_general"],
			"compensacion_anterior": result["cuotas_compensar_anteriores"],
			"resultado_final": resultado,
			"tipo": tipo_resultado,
		},
		"formatted_response": "\n".join(lines),
	}
