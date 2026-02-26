"""
Tool for analyzing Spanish payslips (nóminas)
Analyzes payroll data and provides insights
"""
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


async def analyze_payslip_tool(
	gross_salary: float,
	net_salary: float,
	irpf_withholding: float,
	ss_contribution: float,
	period_month: int,
	period_year: int,
	**kwargs
) -> Dict[str, Any]:
	"""
	Analiza los datos de una nómina española y proporciona información útil.
	
	Args:
		gross_salary: Salario bruto mensual en euros
		net_salary: Salario neto mensual en euros
		irpf_withholding: Retención de IRPF en euros
		ss_contribution: Cotización a la Seguridad Social en euros
		period_month: Mes de la nómina (1-12)
		period_year: Año de la nómina
		**kwargs: Campos adicionales opcionales
		
	Returns:
		Dict con análisis de la nómina
	"""
	try:
		logger.info(f"Analyzing payslip: {period_month}/{period_year}, gross={gross_salary}")

		# Fetch expected SS percentage from DB (data-driven, no hardcoded)
		expected_ss_percentage = 6.35  # fallback default
		try:
			from app.utils.tax_parameter_repository import TaxParameterRepository
			from app.database.turso_client import get_db_client
			db = await get_db_client()
			repo = TaxParameterRepository(db)
			expected_ss_percentage = await repo.get_param(
				'trabajo', 'ss_empleado_pct', period_year, default=6.35
			)
		except Exception as e:
			logger.warning(f"Could not fetch SS pct from DB, using default: {e}")

		# Calcular porcentajes
		irpf_percentage = (irpf_withholding / gross_salary * 100) if gross_salary > 0 else 0
		ss_percentage = (ss_contribution / gross_salary * 100) if gross_salary > 0 else 0
		total_deductions = irpf_withholding + ss_contribution
		deductions_percentage = (total_deductions / gross_salary * 100) if gross_salary > 0 else 0
		
		# Calcular salario anual proyectado
		annual_gross = gross_salary * 12
		annual_net = net_salary * 12
		annual_irpf = irpf_withholding * 12
		annual_ss = ss_contribution * 12
		
		# Análisis de tramos de salario
		if gross_salary < 1000:
			salary_range = "bajo"
			recommendation = "Salario por debajo del SMI. Verifica que se cumple con el Salario Mínimo Interprofesional."
		elif gross_salary < 2000:
			salary_range = "medio-bajo"
			recommendation = "Salario en rango medio-bajo. Podrías beneficiarte de deducciones por familia numerosa o discapacidad."
		elif gross_salary < 3000:
			salary_range = "medio"
			recommendation = "Salario en rango medio. Considera optimizar deducciones por vivienda habitual o aportaciones a planes de pensiones."
		elif gross_salary < 5000:
			salary_range = "medio-alto"
			recommendation = "Salario en rango medio-alto. Evalúa aportaciones a planes de pensiones para reducir base imponible."
		else:
			salary_range = "alto"
			recommendation = "Salario en rango alto. Importante optimizar deducciones y considerar asesoramiento fiscal profesional."
		
		# Análisis de retención de IRPF
		if irpf_percentage < 10:
			irpf_analysis = "Retención baja, típica de salarios bajos o con muchas deducciones."
		elif irpf_percentage < 20:
			irpf_analysis = "Retención normal para salarios medios."
		elif irpf_percentage < 30:
			irpf_analysis = "Retención elevada, típica de salarios medios-altos."
		else:
			irpf_analysis = "Retención muy alta, corresponde a salarios altos."
		
		# Análisis de cotizaciones SS (expected_ss_percentage fetched from DB above)
		if abs(ss_percentage - expected_ss_percentage) > 1:
			ss_analysis = f"Cotización atípica ({ss_percentage:.2f}%). Verifica que incluya contingencias comunes (4.7%), desempleo (1.55%) y formación (0.1%)."
		else:
			ss_analysis = f"Cotización estándar ({ss_percentage:.2f}%), dentro del rango esperado."
		
		# Generar resumen formateado
		summary = f"""📊 ANÁLISIS DE NÓMINA {period_month}/{period_year}

💰 Resumen Mensual:
- Salario bruto: {gross_salary:,.2f}€
- Retención IRPF: {irpf_withholding:,.2f}€ ({irpf_percentage:.2f}%)
- Cotización SS: {ss_contribution:,.2f}€ ({ss_percentage:.2f}%)
- Total deducciones: {total_deductions:,.2f}€ ({deductions_percentage:.2f}%)
- Salario neto: {net_salary:,.2f}€

📈 Proyección Anual:
- Bruto anual: {annual_gross:,.2f}€
- IRPF anual: {annual_irpf:,.2f}€
- SS anual: {annual_ss:,.2f}€
- Neto anual: {annual_net:,.2f}€

🎯 Análisis:
- Rango salarial: {salary_range}
- IRPF: {irpf_analysis}
- Seguridad Social: {ss_analysis}

💡 Recomendación:
{recommendation}

⚠️ Importante: Este análisis es orientativo. Para optimizar tu situación fiscal, consulta con un asesor profesional."""
		
		return {
			"success": True,
			"period": f"{period_month}/{period_year}",
			"monthly": {
				"gross_salary": gross_salary,
				"net_salary": net_salary,
				"irpf_withholding": irpf_withholding,
				"irpf_percentage": round(irpf_percentage, 2),
				"ss_contribution": ss_contribution,
				"ss_percentage": round(ss_percentage, 2),
				"total_deductions": round(total_deductions, 2),
				"deductions_percentage": round(deductions_percentage, 2)
			},
			"annual": {
				"gross": round(annual_gross, 2),
				"net": round(annual_net, 2),
				"irpf": round(annual_irpf, 2),
				"ss": round(annual_ss, 2)
			},
			"analysis": {
				"salary_range": salary_range,
				"irpf_analysis": irpf_analysis,
				"ss_analysis": ss_analysis,
				"recommendation": recommendation
			},
			"formatted_response": summary
		}
	
	except Exception as e:
		logger.error(f"Error analyzing payslip: {e}", exc_info=True)
		return {
			"success": False,
			"error": str(e),
			"formatted_response": f"Error al analizar la nómina: {str(e)}"
		}


# Tool definition para OpenAI function calling
PAYSLIP_ANALYSIS_TOOL = {
	"type": "function",
	"function": {
		"name": "analyze_payslip",
		"description": "Analiza una nómina española y proporciona insights sobre salario, retenciones IRPF, cotizaciones a la Seguridad Social y recomendaciones fiscales. Calcula proyecciones anuales y compara con rangos salariales estándar.",
		"parameters": {
			"type": "object",
			"properties": {
				"gross_salary": {
					"type": "number",
					"description": "Salario bruto mensual en euros"
				},
				"net_salary": {
					"type": "number",
					"description": "Salario neto mensual en euros"
				},
				"irpf_withholding": {
					"type": "number",
					"description": "Retención de IRPF en euros"
				},
				"ss_contribution": {
					"type": "number",
					"description": "Cotización a la Seguridad Social del trabajador en euros"
				},
				"period_month": {
					"type": "integer",
					"description": "Mes de la nómina (1-12)"
				},
				"period_year": {
					"type": "integer",
					"description": "Año de la nómina"
				}
			},
			"required": ["gross_salary", "net_salary", "irpf_withholding", "ss_contribution", "period_month", "period_year"]
		}
	}
}