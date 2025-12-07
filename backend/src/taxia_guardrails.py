import re
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from config import settings

logger = logging.getLogger(__name__)


class GuardType(Enum):
	INPUT = "input"
	OUTPUT = "output"


@dataclass
class GuardResult:
	"""Resultado de aplicar un guardrail"""
	passed: bool
	content: str
	violations: List[str]
	guard_type: GuardType
	original_content: Optional[str] = None


class TaxEvasionGuard:
	"""Guardrail personalizado para detectar consultas sobre evasión fiscal"""
	
	def __init__(self):
		self.forbidden_patterns = [
			r"\b(ocultar|esconder)\s+(ingresos|dinero|beneficios)\b",
			r"\bno\s+declarar\s+parte\s+de\b",
			r"\b(no\s+declarar|sin\s+declarar)\s+(ingresos|IVA|beneficios)\b",
			r"\b(evadir|esquivar|evitar)\s+(impuestos|fiscalidad|hacienda)\b",
			r"\b(fraude|defraudar)\s+(fiscal|tributario|hacienda)\b",
			r"\b(dinero\s+)?en\s+negro\b",
			r"\b(sin\s+factura|facturas\s+falsas)\b",
			r"\b(sociedades?\s+pantalla|testaferros?)\b",
			r"\b(paraísos?\s+fiscales?)\s+para\s+(ocultar|esconder)\b"
		]
	
	def validate(self, text: str) -> GuardResult:
		"""Valida si el texto contiene consultas sobre evasión fiscal"""
		violations = []
		
		# Buscar patrones prohibidos
		for pattern in self.forbidden_patterns:
			if re.search(pattern, text, re.IGNORECASE):
				violations.append(f"Patrón de evasión detectado: {pattern}")
		
		if violations:
			safe_response = self._get_refusal_response()
			return GuardResult(
				passed=False,
				content=safe_response,
				violations=violations,
				guard_type=GuardType.INPUT,
				original_content=text
			)
		
		return GuardResult(
			passed=True,
			content=text,
			violations=[],
			guard_type=GuardType.INPUT,
			original_content=text
		)
	
	def _get_refusal_response(self) -> str:
		"""Respuesta estándar para consultas sobre evasión fiscal"""
		return (
			"**Veredicto corto:** No puedo ayudarte con esa consulta.\n"
			"**Resumen entendible:** No proporciono asesoramiento para evadir obligaciones fiscales. "
			"Sí puedo ayudarte con declaraciones complementarias, regularización voluntaria y cumplimiento normativo.\n"
			"**Por qué:**\n"
			"- Debes cumplir la normativa tributaria vigente.\n"
			"- El incumplimiento tiene sanciones y recargos.\n"
			"- Puedo orientarte sobre vías de regularización legal.\n"
			"**Modelos/Formularios (si aplica):** Declaraciones complementarias según el impuesto afectado.\n"
			"**Qué debes comprobar o aportar:**\n"
			"- Períodos afectados e importes.\n"
			"- Documentación soporte (facturas, extractos, nóminas).\n"
			"- Situación por impuesto (IVA/IRPF/IS) para ver el trámite correcto.\n"
			"**Ejemplo rápido (opcional):** Presentar declaración complementaria del período afectado con los importes omitidos.\n"
			"**Citas (mín. 2):**\n"
			"- Manual práctico de Renta 2024 (obligaciones), p. X\n"
			"- Manual práctico IVA 2024 (rectificativas), p. X\n"
			"**Aviso:** Esto no constituye asesoramiento profesional. Verifícalo con tu asesor."
		)


class TaxIAGuardrails:
	"""Sistema simplificado de guardrails para TaxIA"""
	
	def __init__(self):
		self.settings = settings
		self.tax_evasion_guard = TaxEvasionGuard()
	
	def validate_input(self, user_input: str) -> GuardResult:
		"""Valida la entrada del usuario"""
		if not self.settings.enable_guardrails:
			return GuardResult(
				passed=True,
				content=user_input,
				violations=[],
				guard_type=GuardType.INPUT
			)
		
		try:
			# Verificar evasión fiscal
			evasion_result = self.tax_evasion_guard.validate(user_input)
			return evasion_result
			
		except Exception as e:
			logger.error(f"Error en validación de entrada: {e}")
			return GuardResult(
				passed=True,  # En caso de error, permitir pasar
				content=user_input,
				violations=[str(e)],
				guard_type=GuardType.INPUT,
				original_content=user_input
			)
	
	def validate_output(self, response: str, context_chunks: List[str] = None) -> GuardResult:
		"""Valida la respuesta generada (simplificado)"""
		if not self.settings.enable_guardrails:
			return GuardResult(
				passed=True,
				content=response,
				violations=[],
				guard_type=GuardType.OUTPUT
			)
		
		try:
			# Por ahora solo devolvemos la respuesta sin modificar
			return GuardResult(
				passed=True,
				content=response,
				violations=[],
				guard_type=GuardType.OUTPUT,
				original_content=response
			)
			
		except Exception as e:
			logger.error(f"Error en validación de salida: {e}")
			return GuardResult(
				passed=True,
				content=response,
				violations=[str(e)],
				guard_type=GuardType.OUTPUT,
				original_content=response
			)


# Instancia global
guardrails_system = TaxIAGuardrails()