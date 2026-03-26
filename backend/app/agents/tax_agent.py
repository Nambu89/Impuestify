"""
TaxAgent - Specialized Tax Assistant Agent

Uses OpenAI API with function calling for tax calculations.
"""
import os
import logging
import asyncio
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime

from openai import OpenAI, AsyncOpenAI

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
	"""Response from the tax agent"""
	content: str
	sources: List[Dict[str, Any]]
	metadata: Dict[str, Any]
	agent_name: str


class TaxAgent:
	"""
	Tax specialist agent using OpenAI API.
	
	Provides intelligent responses about Spanish tax regulations
	based on AEAT documentation.
	
	Features:
	- RAG integration for document retrieval
	- Function calling for tax calculations
	- Web search for updated regulations
	- Conversational and empathetic responses
	"""
	
	def __init__(
		self,
		name: str = "TaxAgent",
		model: Optional[str] = None,
		api_key: Optional[str] = None
	):
		"""
		Initialize TaxAgent.
		
		Args:
			name: Agent name
			model: OpenAI model name (gpt-5-mini, gpt-5, gpt-5.1, etc.)
			api_key: OpenAI API key
		"""
		from app.config import settings
		self.name = name
		self.model = model or settings.OPENAI_MODEL
		self.api_key = api_key or settings.OPENAI_API_KEY
		
		# Fecha actual para cálculos fiscales
		self.current_date = datetime.now()
		self.current_year = self.current_date.year
		self.current_month = self.current_date.month
		
		# Determinar año fiscal para IRPF
		# REGLA: El IRPF se declara el año siguiente
		# - Estamos en 2025 → Los cálculos son para IRPF de 2024 (declaración en abril-junio 2025)
		# - Estamos en 2026 → Los cálculos son para IRPF de 2025 (declaración en abril-junio 2026)
		self.irpf_declaration_year = self.current_year  # Año en que se declara
		self.irpf_fiscal_year = self.current_year - 1   # Año fiscal que se declara
		
		# Para cuotas de autónomos, siempre es el año actual
		self.autonomous_quota_year = self.current_year
		
		self._client = None
		
		self._initialize()
	
	def _initialize(self):
		"""Initialize the OpenAI client."""
		if self.api_key:
			self._client = OpenAI(api_key=self.api_key)
			self._async_client = AsyncOpenAI(api_key=self.api_key)
			logger.info(f"TaxAgent '{self.name}' initialized (year: {self.current_year}, IRPF fiscal: {self.irpf_fiscal_year}, quota: {self.autonomous_quota_year})")
		else:
			logger.error("TaxAgent initialization failed - missing OPENAI_API_KEY")
			raise ValueError("OPENAI_API_KEY is required")
	
	def _get_system_prompt(self) -> str:
		"""Genera el system prompt con la fecha actual y lógica de años fiscales"""

		# Determinar periodo de campaña de renta
		if 4 <= self.current_month <= 6:
			irpf_context = f"Campaña de la Renta {self.irpf_declaration_year} activa — declarando ingresos de {self.irpf_fiscal_year}."
		else:
			irpf_context = f"Próxima declaración en {self.irpf_declaration_year + 1} (ingresos de {self.current_year})."

		return f"""Eres Impuestify, experto en fiscalidad española. Respondes con datos concretos, cifras y referencias legales. Tuteas al usuario, eres claro y directo — sin rodeos ni florituras. Lenguaje natural, evita jerga excesiva.

## CONTEXTO TEMPORAL
- Fecha: {self.current_date.strftime('%d de %B de %Y')} | Año actual: {self.current_year}
- IRPF: {irpf_context} Si el usuario no especifica año, usa {self.irpf_fiscal_year}.
- Cuotas autónomos: siempre año {self.autonomous_quota_year} (se pagan en el año en curso).

## REGLA DE ORO: RESPONDE LO QUE PREGUNTAN
- Responde EXACTAMENTE a lo que el usuario pregunta. NO calcules IRPF ni lances deducciones si no lo piden.
- Si preguntan sobre un epígrafe IAE → responde sobre IAE. Si preguntan sobre IVA → responde sobre IVA. Si preguntan "cuánto pago" → ahí sí usa simulate_irpf.
- Usa herramientas SOLO cuando la pregunta lo requiera. NO uses simulate_irpf ni discover_deductions por defecto.
- El perfil fiscal inyectado es contexto — úsalo para personalizar respuestas, NO para lanzar cálculos no solicitados.
- Si falta un dato imprescindible para responder, da la respuesta más completa posible y pregunta ESE dato. NUNCA más de 1 pregunta a la vez.
- "Cobro X€" sin especificar → asume bruto. Explícalo al final.

## REGLA CRITICA: NO NARRAR PROCESOS INTERNOS — RESPONDE SIEMPRE
- NUNCA escribas al usuario frases como "Voy a buscar...", "Déjame consultar...", "Realizando búsqueda...", "No he encontrado en el catálogo...", "Voy a volver a buscar con otros términos...", "Te digo lo que encuentre...", "¿De acuerdo?".
- NUNCA pidas permiso para responder. NUNCA preguntes "¿Quieres que busque?". RESPONDE DIRECTAMENTE.
- El usuario NO debe ver tus pasos de razonamiento ni tus intentos de búsqueda. Solo ve el RESULTADO final.
- Si una herramienta no devuelve resultados, RESPONDE INMEDIATAMENTE con tu conocimiento experto. Eres un asesor fiscal con conocimiento completo de la normativa española — úsalo.
- Si necesitas hacer múltiples búsquedas, hazlas en silencio y presenta solo la respuesta consolidada.
- NUNCA devuelvas una respuesta vacía o que solo pida confirmación. Cada mensaje tuyo DEBE contener información útil.
- Ejemplo MALO: "Voy a buscar en el catálogo IAE... No encuentro resultados... Te digo lo que encuentre, ¿de acuerdo?"
- Ejemplo BUENO: "El epígrafe IAE para una explotación de ponedoras de huevos en Bizkaia es el **019.3 — Avicultura de puesta** (Tarifas IAE, Sección 1ª, División 0). En Bizkaia, al estar en régimen foral, debes darte de alta en la Hacienda Foral de Bizkaia (no en la AEAT). La normativa aplicable es la Norma Foral 2/2005 de Bizkaia sobre el IAE."

## REGLA CRITICA: DATOS DE DOCUMENTOS ANALIZADOS > PERFIL FISCAL
- Si en la conversación hay un análisis previo de nómina, factura u otro documento con cifras concretas (bruto, neto, IRPF, SS, bonus, etc.), esos datos tienen PRIORIDAD ABSOLUTA sobre el perfil fiscal genérico.
- Cuando el usuario haga preguntas de seguimiento sobre ese documento (ej: "sin el bonus", "recalcula con 14 pagas", "qué pasa si subo la retención"), USA LAS CIFRAS DEL DOCUMENTO ANALIZADO, no las del perfil.
- Para recalcular: extrae los datos del análisis previo en la conversación, aplica el ajuste que pide el usuario, y calcula con esos números.
- Ejemplo: si la nómina muestra bruto=4.583€ con bonus=1.440€ y el usuario dice "sin el bonus" → usa (4.583 - 1.440) = 3.142€ mensual como base, NO el bruto del perfil.

## HERRAMIENTAS
- **simulate_irpf**: Herramienta principal para IRPF. Pasa ingresos brutos + CCAA del perfil. Calcula gastos, reducción trabajo, MPYF, tarifa general y ahorro, deducciones autonómicas. También acepta: aportaciones_plan_pensiones, hipoteca_pre2013, madre_trabajadora_ss, familia_numerosa, donativos_ley_49_2002, retenciones_trabajo, tributacion_conjunta, alquiler_pre2015, rentas_imputadas_catastral. Pasa estos parámetros directamente desde el perfil fiscal si están disponibles.
- **calculate_irpf**: Solo si el usuario da la base liquidable directamente (sin necesidad de calcular gastos/reducciones).
- **calculate_autonomous_quota**: Cuotas autónomos año {self.autonomous_quota_year}. Si usuario dice "facturación bruta", aplica deducción del 7% (rendimiento_neto = X × 0.93) antes de pasar al tool.
- **calculate_modelo_303**: IVA/IGIC trimestral. PASA SIEMPRE la ccaa del usuario. Si Canarias → calcula IGIC 7% (Modelo 420, Gobierno de Canarias; el Modelo 349 NO aplica desde Canarias). Si Gipuzkoa → Modelo 300 + TicketBAI. Si Navarra → F69. Si Bizkaia → 303 foral + BATUZ/TicketBAI. Si Araba → 303 foral + TicketBAI. Si Ceuta/Melilla → redirige a calculate_modelo_ipsi. Resto → Modelo 303 AEAT. Datos acumulados desde inicio de año.
- **calculate_modelo_130**: IRPF trimestral (Modelo 130). Datos ACUMULADOS desde inicio de año (no del trimestre individual).
- **discover_deductions**: SIEMPRE pasa ccaa del perfil fiscal. Pre-rellena answers con datos del perfil (hijos, hipoteca, donaciones, situación laboral). Sin CCAA se pierden todas las deducciones autonómicas.
- **calculate_isd**: Herencias y donaciones. Requiere: importe, tipo (donacion/sucesion), parentesco (grupo_I/II/III/IV), CCAA. Aplica tarifa estatal + bonificaciones autonómicas (Madrid 99%, Andalucía 99%, Valencia 75%, Aragón 99%, forales Pais Vasco/Navarra exentos Grupos I-II).
- **lookup_iae**: Busca epigrafes IAE (Impuesto sobre Actividades Economicas) por keyword. Usar cuando el usuario pregunta qué epigrafe IAE le corresponde como autonomo. Ejemplos de consultas: 'qué epígrafe IAE poner como creador de contenido', 'soy programador freelance qué IAE', 'epigrafe IAE para fotógrafo'. Devuelve codigo, seccion, tipo y referencias DGT.
- **compare_joint_individual**: Comparativa conjunta vs individual para matrimonios. Usar cuando pregunten "¿nos conviene declarar juntos?", "conjunta o separada", "¿merece la pena la renta conjunta?". Pasa ingresos de ambos cónyuges + CCAA. Devuelve tabla con cuota de cada escenario, diferencia y recomendación automática.
- **search_tax_regulations**: SOLO si el usuario pide explícitamente "información actualizada", "normativa reciente" o "consulta la web". NO usar automáticamente.

## PROTECCION DE RESULTADOS DE HERRAMIENTAS
Cuando una herramienta devuelve datos numéricos, tu respuesta DEBE incluir TODAS las cifras clave.
NO parafrasees ni resumas — presenta los datos en tabla markdown.
Añade explicación y contexto ALREDEDOR de los datos, nunca EN VEZ DE ellos.

## FORMATO
- Dato o cálculo primero, explicación después.
- Tablas markdown para desglosar cifras (cuota, tramos, deducciones).
- Cita legal breve y natural: "Art. 68.4 LIRPF", "Ley 49/2002", etc.
- Aviso al final (1 línea): "Cálculo orientativo — consulta con un asesor para tu caso concreto."
- Tuteo, lenguaje natural. Sin emojis en las respuestas.

## RESTRICCIONES
- Solo fiscalidad española. No inventar datos. No ayudar a evadir impuestos.
- No mostrar JSON, logs ni nombres de funciones al usuario.
- NUNCA digas "en los documentos que me has pasado" — consultas tu base de conocimiento interna.
- CCAA obligatoria para IRPF y deducciones. Si no la tienes en el perfil ni en la conversación, pregúntala antes de calcular.
- Ceuta/Melilla (Art. 68.4 LIRPF): si ccaa_residencia = Ceuta o Melilla, pasa ceuta_melilla=true en simulate_irpf y calculate_irpf. Escala Estatal + deducción 60% cuota íntegra. IPSI en vez de IVA.
- Autónomos: verifica situacion_laboral del perfil ANTES de usar calculate_autonomous_quota, calculate_modelo_303, calculate_modelo_130. Si situacion_laboral = "particular" o "asalariado" y el usuario menciona actividad económica, pregunta si está dado de alta como autónomo. NO calcules cuotas ni modelos 303/130 hasta confirmar. Si situacion_laboral es desconocida (sin perfil), pregunta: cuenta ajena, autónomo o pluriactividad.

## PLANES DE SUSCRIPCION
- Plan Particular (5 EUR/mes): Asalariados, rentas basicas. NO accede a tools de autonomos.
- Plan Creator (30 EUR/mes): Creadores de contenido, influencers, YouTubers, streamers. Acceso completo + guia especializada.
- Plan Autonomo (39 EUR/mes): Autonomos clasicos, freelancers, emprendedores. Acceso completo.

## FISCALIDAD DE CREADORES DE CONTENIDO
Si el usuario menciona YouTube, TikTok, Twitch, Instagram, Patreon, OnlyFans, Substack, streaming, influencer, creador de contenido, o sponsorship:

1. **Epigrafe IAE**: El correcto es 8690 seccion 2 (DGT V0773-22). Usa la tool lookup_iae para buscar.
2. **IVA por plataforma**:
   - YouTube/Google (Irlanda), Meta (Irlanda), Twitch (Luxemburgo) → Intracomunitaria SIN IVA, obligacion Modelo 349
   - TikTok (UK), OnlyFans (UK) → Exportacion SIN IVA (fuera UE)
   - Sponsors espanoles → CON IVA 21%
3. **Retencion**: Las plataformas extranjeras NO practican retencion IRPF. El creador debe hacer pagos fraccionados (Modelo 130).
4. **Derechos de autor / Royalties**: Retencion del 24% (no 15%) cuando el pagador es empresa espanola.
5. **Modelo 349**: Obligatorio si factura a Google Ireland, Meta Ireland, Twitch Luxembourg. Trimestral si >50.000 EUR, anual si menos.
6. **DAC7 / Modelo 238**: Desde enero 2026, las plataformas reportan a Hacienda los ingresos de los creadores. El usuario DEBE declarar.
7. **CNAE-2025**: Nuevo codigo 60.39 para creadores de contenido digital (RD 10/2025).
8. **Plan Tributario AEAT 2026**: Hacienda ha puesto a los influencers como objetivo prioritario de inspeccion.

## USUARIOS CON MULTIPLES ROLES (NO EXCLUYENTES)
Un usuario puede ser asalariado + autonomo + creador de contenido + inversor + propietario simultaneamente.
- Lee el perfil completo (situacion_laboral + roles_adicionales) ANTES de responder.
- No asumas que solo tiene un tipo de renta. Si el perfil muestra multiples roles, considera TODOS.
- TODAS las rentas se suman en la declaracion:
  - Trabajo (nomina) + Actividad economica (facturas) + Alquiler → base imponible general
  - Intereses + dividendos + ganancias patrimoniales → base del ahorro
- Obligaciones por rol: Modelo 303/130 solo si es autonomo/creador. Modelo 349 solo si factura a UE.
- La tributacion conjunta afecta a TODAS las rentas del matrimonio.
- NO fuerces al usuario a elegir un solo rol. Responde considerando toda su situacion.

## VARIACIONES TERRITORIALES PARA CREADORES
- **Gipuzkoa**: Modelo 300 (NO 303) para IVA trimestral. TicketBAI obligatorio.
- **Navarra**: Modelo F69 (NO 303) para IVA. Modelos 715 (retenciones) y 759 (alquileres) en vez de 111/115.
- **Bizkaia**: Modelo 303 foral + BATUZ (envio continuo facturas). TicketBAI obligatorio.
- **Araba**: Modelo 303 foral. TicketBAI obligatorio.
- **Canarias**: Modelo 420 IGIC (NO 303 IVA). Modelo 425 resumen anual. El Modelo 349 NO aplica desde Canarias (no es territorio IVA armonizado UE). REF Canarias puede beneficiar a creadores con SL.
- **Ceuta/Melilla**: IPSI (2-4%) en vez de IVA (21%). Deduccion 60% IRPF. Bonificacion 50% cuotas SS. Muy atractivo para nomadas digitales pero requiere residencia real.
- **Modelo 721**: Criptomonedas en exchanges extranjeros (desde 2023, sustituye al 720 para cripto). Plazo: hasta 31 marzo.

## COMPARATIVAS MULTI-ESCENARIO
Si el usuario pide "comparativa", "diferencia entre", "qué me conviene más", "cuál es mejor", "conjunta vs individual", "autónomo vs asalariado" o similar:
- Llama a simulate_irpf MÚLTIPLES VECES en la misma respuesta con los parámetros contrastantes (ej: tributacion_conjunta=true y tributacion_conjunta=false).
- El modelo puede proponer varias tool calls en paralelo — TODAS se ejecutarán.
- Presenta ambos resultados en tabla markdown comparativa con columnas Escenario A / Escenario B.
- Indica claramente cuál opción es más favorable y la diferencia exacta en euros."""
	
	def _filter_bad_responses(self, content: str, original_query: str) -> str:
		"""Filter out LLM responses that ask permission instead of answering."""
		import re
		if not content or len(content.strip()) < 20:
			return content

		content_lower = content.lower()

		# Detect permission-asking patterns
		permission_patterns = [
			"te digo lo que encuentre",
			"¿de acuerdo?",
			"¿quieres que busque",
			"¿te parece",
			"si el catálogo oficial no carga",
			"¿deseas que",
			"¿procedo a",
			"voy a intentar",
			"déjame ver si",
		]

		is_permission_asking = any(p in content_lower for p in permission_patterns)

		# Also detect if response is too short and just asks something
		is_too_short_question = len(content.strip()) < 200 and "?" in content

		if is_permission_asking or (is_too_short_question and not any(c.isdigit() for c in content)):
			logger.warning(f"🚫 Filtered permission-asking response. Regenerating with knowledge.")
			# Return a direct answer using the agent's knowledge
			return (
				f"No he encontrado datos específicos en mis fuentes para tu consulta exacta, "
				f"pero puedo orientarte con mi conocimiento de la normativa fiscal española.\n\n"
				f"Para consultas sobre epígrafes IAE, modelos tributarios o normativa específica de un territorio, "
				f"te recomiendo consultar directamente:\n"
				f"- **AEAT**: sede.agenciatributaria.gob.es (territorio común)\n"
				f"- **Hacienda Foral de Bizkaia**: web.bizkaia.eus/es/hacienda (Bizkaia/BATUZ)\n"
				f"- **Hacienda Foral de Gipuzkoa**: www.gipuzkoa.eus/es/hacienda (Gipuzkoa/TicketBAI)\n"
				f"- **Hacienda Foral de Araba**: web.araba.eus/es/hacienda (Araba/TicketBAI)\n"
				f"- **Hacienda Foral de Navarra**: hacienda.navarra.es (Navarra)\n\n"
				f"Si me das más contexto sobre tu actividad, puedo ayudarte a identificar el epígrafe más probable."
			)

		return content

	async def run(
		self,
		query: str,
		context: str = "",
		sources: List[dict] = None,
		conversation_history: List[dict] = None,
		use_tools: bool = True,
		system_prompt: Optional[str] = None,
		model: Optional[str] = None,  # Dynamic model selection
		user_id: Optional[str] = None,  # User ID for audit logging
		progress_callback: Optional[Any] = None,  # For SSE streaming
		db_client: Optional[Any] = None,  # Database client for memory
		restricted_mode: bool = False,  # Salaried-only: block autonomo tools
		fiscal_profile: Optional[Dict[str, Any]] = None  # Autonomo fiscal profile
	) -> AgentResponse:
		"""
		Returns:
			AgentResponse with answer and metadata
		"""
		# === MEMORY: Extract and store user facts ===
		user_memory_context = ""
		if user_id:
			try:
				from app.services.user_memory_service import get_user_memory_service
				memory_service = get_user_memory_service(db_client)
				
				# Process message to extract facts
				memory_result = await memory_service.process_message_for_memory(user_id, query)
				
				# Get user context (CCAA, employment, etc.)
				user_context = memory_result.get("context", {})
				
				# Build comprehensive user context string
				context_parts = []
				
				if user_context.get("ccaa"):
					context_parts.append(f"Residencia: {user_context['ccaa']}")
					logger.info(f"🧠 User memory context: CCAA={user_context['ccaa']}")
				
				if user_context.get("employment"):
					context_parts.append(f"Situación laboral: {user_context['employment']}")
				
				# NEW: Add numeric fields
				if user_context.get("edad"):
					context_parts.append(f"Edad: {user_context['edad']} años")
				
				if user_context.get("ingresos_brutos"):
					context_parts.append(f"Ingresos brutos anuales: {user_context['ingresos_brutos']}€")
				
				if user_context.get("donation_pending"):
					donation_type = user_context.get("donation_type", "dinero")
					donation_from = user_context.get("donation_from", "familiar")
					context_parts.append(
						f"Donación pendiente: {user_context['donation_pending']}€ "
						f"(tipo: {donation_type}, de: {donation_from})"
					)
				
				if user_context.get("facts"):
					context_parts.append(f"Hechos recordados: {'; '.join(user_context['facts'][:3])}")
				
				# Build context string
				if context_parts:
					user_memory_context = "\n\n📍 **CONTEXTO DEL USUARIO (IMPORTANTE - USA ESTA INFO)**:\n" + "\n".join([f"- {part}" for part in context_parts])
					user_memory_context += "\n\n⚠️ IMPORTANTE: Antes de responder, consulta siempre esta información del usuario. No pijas datos que ya conoces."
					
			except Exception as e:
				logger.warning(f"⚠️ User memory error (continuing without memory): {e}")
		
		# === FISCAL PROFILE: Inject user fiscal data into context ===
		# Always inject situacion_laboral prominently (even for "particular")
		if fiscal_profile:
			fp_lines = []
			# Highlight employment status at the top
			sit_laboral = fiscal_profile.get("situacion_laboral", "")
			roles_adicionales = fiscal_profile.get("roles_adicionales", [])
			if isinstance(roles_adicionales, str):
				import json as _json
				try:
					roles_adicionales = _json.loads(roles_adicionales)
				except Exception:
					roles_adicionales = []

			if sit_laboral and sit_laboral.lower() in ("particular", "asalariado"):
				if roles_adicionales:
					fp_lines.append(f"- Situación laboral principal: {sit_laboral}")
					fp_lines.append(f"- Roles adicionales: {', '.join(roles_adicionales)}")
					fp_lines.append("- ⚠️ Este usuario tiene MÚLTIPLES roles fiscales. Considera TODAS sus fuentes de renta al responder.")
				else:
					fp_lines.append(f"- ⚠️ Situación laboral: {sit_laboral} (NO es autónomo — NO usar herramientas de autónomos sin preguntar)")
			elif roles_adicionales:
				fp_lines.append(f"- Situación laboral principal: {sit_laboral}")
				fp_lines.append(f"- Roles adicionales: {', '.join(roles_adicionales)}")
				fp_lines.append("- ⚠️ Este usuario tiene MÚLTIPLES roles fiscales. Considera TODAS sus fuentes de renta al responder.")
			label_map = {
				"ccaa_residencia": "CCAA residencia",
				"situacion_laboral": "Situación laboral",
				"epigrafe_iae": "Epígrafe IAE",
				"tipo_actividad": "Tipo actividad",
				"fecha_alta_autonomo": "Fecha alta autónomo",
				"metodo_estimacion_irpf": "Método estimación IRPF",
				"regimen_iva": "Régimen IVA",
				"rendimientos_netos_mensuales": "Rendimientos netos mensuales",
				"base_cotizacion_reta": "Base cotización RETA",
				"territorio_foral": "Territorio foral",
				"territorio_historico": "Territorio histórico",
				"tipo_retencion_facturas": "Retención facturas",
				"tarifa_plana": "Tarifa plana",
				"pluriactividad": "Pluriactividad",
				"ceuta_melilla": "Residente en Ceuta/Melilla",
				# Phase 1: IRPF deductions / reductions
				"aportaciones_plan_pensiones": "Aportaciones plan pensiones",
				"aportaciones_plan_pensiones_empresa": "Aportaciones plan pensiones (empresa)",
				"hipoteca_pre2013": "Hipoteca pre-2013",
				"capital_amortizado_hipoteca": "Capital amortizado hipoteca",
				"intereses_hipoteca": "Intereses hipoteca",
				"madre_trabajadora_ss": "Madre trabajadora con SS",
				"gastos_guarderia_anual": "Gastos guardería anuales",
				"familia_numerosa": "Familia numerosa",
				"tipo_familia_numerosa": "Tipo familia numerosa",
				"donativos_ley_49_2002": "Donativos Ley 49/2002",
				"donativo_recurrente": "Donativo recurrente (>=2 años)",
				"retenciones_trabajo": "Retenciones trabajo",
				"retenciones_alquiler": "Retenciones alquiler",
				"retenciones_ahorro": "Retenciones ahorro",
			}
			for key, label in label_map.items():
				val = fiscal_profile.get(key)
				if val is not None and val != "":
					if isinstance(val, bool):
						fp_lines.append(f"- {label}: {'Sí' if val else 'No'}")
					elif isinstance(val, float) and key == "tipo_retencion_facturas":
						fp_lines.append(f"- {label}: {val}%")
					else:
						fp_lines.append(f"- {label}: {val}")
			if fp_lines:
				is_autonomo_profile = sit_laboral.lower() in ("autónomo", "autonomo", "pluriactividad") if sit_laboral else False
				has_creator_role = "creador_contenido" in roles_adicionales
				has_multi_roles = len(roles_adicionales) > 0
				if is_autonomo_profile or has_creator_role:
					fiscal_context = "\n\n📋 **PERFIL FISCAL DE AUTÓNOMO** (usa estos datos para pre-rellenar herramientas):\n" + "\n".join(fp_lines)
					fiscal_context += "\n\n⚠️ Usa el perfil fiscal para pre-rellenar parámetros de calculate_modelo_303, calculate_modelo_130 y calculate_autonomous_quota."
				else:
					fiscal_context = "\n\n📋 **PERFIL FISCAL DEL USUARIO**:\n" + "\n".join(fp_lines)
					fiscal_context += "\n\n⚠️ Este usuario NO es autónomo. Si menciona ingresos por actividad económica, PREGUNTA si está dado de alta como autónomo antes de usar herramientas de autónomos."
				user_memory_context = fiscal_context + user_memory_context

		# === SECURITY: Content Moderation (Llama Guard) ===
		try:
			from app.security.llama_guard import get_llama_guard
			from app.security.audit_logger import audit_logger
			
			llama_guard = get_llama_guard()
			moderation_result = await llama_guard.moderate(query)
			
			if not moderation_result.is_safe:
				# Log the moderation block
				audit_logger.log_moderation_block(
					user_id=user_id or "anonymous",
					categories=moderation_result.blocked_categories
				)
				
				# Return user-friendly block message
				block_message = llama_guard.get_block_message(moderation_result.blocked_categories)
				logger.warning(f"🚫 Content blocked by Llama Guard: {moderation_result.blocked_categories}")
				
				return AgentResponse(
					content=block_message,
					sources=[],
					metadata={
						"moderated": True,
						"blocked_categories": moderation_result.blocked_categories,
						"risk_level": moderation_result.risk_level
					},
					agent_name=self.name
				)
		except ImportError:
			logger.debug("Llama Guard not available, skipping content moderation")
		except Exception as e:
			logger.warning(f"⚠️ Content moderation error (failing open): {e}")
		
		# === SPEED: Semantic Cache Check ===
		try:
			from app.security.semantic_cache import get_semantic_cache

			semantic_cache = get_semantic_cache()
			cache_result = await semantic_cache.get_similar(query)

			if cache_result.hit:
				# Reject stale cached responses that indicate RAG failure
				_bad_cache_patterns = [
					"no he encontrado datos",
					"no he encontrado información específica",
					"te recomiendo consultar directamente",
					"no dispongo de información específica",
				]
				cached_lower = (cache_result.response or "").lower()
				is_stale = any(p in cached_lower for p in _bad_cache_patterns)
				if is_stale:
					print(f"🗑️ Semantic Cache REJECTED stale response (similarity={cache_result.similarity:.3f})", flush=True)
				else:
					print(f"💾 Semantic Cache HIT (similarity={cache_result.similarity:.3f})", flush=True)
					return AgentResponse(
						content=cache_result.response,
						sources=sources or [],
						metadata={
							"cache_hit": True,
							"similarity": cache_result.similarity,
							"model": self.model,
							"agent": self.name
						},
						agent_name=self.name
					)
		except ImportError:
			logger.debug("Semantic Cache not available, skipping cache lookup")
		except Exception as e:
			logger.warning(f"⚠️ Semantic cache error (proceeding without cache): {e}")
		
		# === SPEED: Complexity Router (Dynamic Model Selection) ===
		selected_model = model or self.model  # Allow override via parameter
		reasoning_effort = "medium"  # Default
		router_confidence = 0.0
		
		try:
			from app.security.complexity_router import classify_complexity
			
			# Get full classification with model recommendation
			complexity_result = classify_complexity(query)
			
			# Use router-recommended model (gpt-5-mini for simple, gpt-5/gpt-5.1 for complex)
			selected_model = complexity_result.model
			reasoning_effort = complexity_result.reasoning_effort.value
			router_confidence = complexity_result.confidence
			
			logger.info(f"🧠 Complexity Router: {complexity_result.level.value} → model={selected_model}, effort={reasoning_effort}, confidence={router_confidence:.2f}")
		except ImportError:
			logger.debug("Complexity Router not available, using default model")
		except Exception as e:
			logger.warning(f"⚠️ Complexity router error: {e}, using default model")
		
		# Build the prompt with context and user memory
		user_message = self._build_prompt(query, context, user_memory_context, fiscal_profile=fiscal_profile)
		
		# Emit initial thinking event (for SSE streaming)
		if progress_callback:
			await progress_callback.thinking("Analizando tu consulta...")
			# Emit second thinking event after a brief delay for memory/security checks
			await progress_callback.thinking("Consultando tu historial y contexto...")
		
		try:
			# Import tools
			from app.tools import ALL_TOOLS, TOOL_EXECUTORS

			# In restricted mode, filter out autonomo-specific tools
			RESTRICTED_TOOL_NAMES = {
				"calculate_autonomous_quota",
				"calculate_modelo_303",
				"calculate_modelo_130",
			}
			if restricted_mode:
				active_tools = [
					t for t in ALL_TOOLS
					if t.get("function", {}).get("name") not in RESTRICTED_TOOL_NAMES
				]
				logger.info(f"Restricted mode: {len(ALL_TOOLS) - len(active_tools)} tools removed")
			else:
				active_tools = ALL_TOOLS

			# Build messages with conversation history
			# Add user memory context to system prompt for better attention
			system_content = system_prompt or self._get_system_prompt()
			if user_memory_context:
				# Prepend user context to system prompt (high priority)
				system_content = user_memory_context + "\n\n" + system_content
			
			messages = [
				{"role": "system", "content": system_content}
			]
			
			# Add conversation history if provided
			if conversation_history:
				for msg in conversation_history:
					messages.append({
						"role": msg.get("role"),
						"content": msg.get("content")
					})
				logger.info(f"Added {len(conversation_history)} messages from conversation history")
			
			# Add current user message
			messages.append({"role": "user", "content": user_message})
			
			# First call with tools (if enabled)
			logger.info(f"Calling OpenAI with model={selected_model}, tools={use_tools}, reasoning_effort={reasoning_effort}")

			if progress_callback:
				await progress_callback.thinking("Procesando tu pregunta...")

			try:
				# Add timeout to prevent indefinite waiting
				response = await asyncio.wait_for(
					asyncio.to_thread(
						self._client.chat.completions.create,
						model=selected_model,  # ← Use router-selected model
						messages=messages,
						tools=active_tools if use_tools else None,
						tool_choice="auto" if use_tools else None,
						temperature=1,
						max_completion_tokens=10000
					),
					timeout=60.0  # 60 second timeout
				)
			except asyncio.TimeoutError:
				logger.error("⏱️ OpenAI call timed out after 60 seconds")
				return AgentResponse(
					content="⏱️ Lo siento, el análisis está tardando más de lo esperado. Por favor, intenta reformular tu pregunta de forma más específica o simplíficala.",
					sources=sources or [],
					metadata={"error": "timeout", "processing_time": 60.0},
					agent_name=self.name
				)
			
			# Check if model wants to call a function
			message = response.choices[0].message
			
			logger.info(f"OpenAI response - has tool_calls: {bool(message.tool_calls)}")
			logger.info(f"OpenAI response - content length: {len(message.content) if message.content else 0}")
			
			if message.tool_calls:
				import json

				# Add assistant message with ALL tool calls (required by OpenAI API)
				messages.append({
					"role": "assistant",
					"content": None,
					"tool_calls": [tc.model_dump() for tc in message.tool_calls]
				})

				# Execute ALL tool calls (supports multi-call comparatives like conjunta vs individual)
				for tool_call in message.tool_calls:
					function_name = tool_call.function.name
					function_args = json.loads(tool_call.function.arguments)

					logger.info(f"Tool called: {function_name} with args: {function_args}")

					# Emit tool call event (for SSE streaming)
					if progress_callback:
						await progress_callback.tool_call(function_name, function_args)

					# Execute the appropriate tool dynamically
					if function_name in TOOL_EXECUTORS:
						tool_executor = TOOL_EXECUTORS[function_name]
						# Inject user_id and db_client for tools that need them
						if function_name == "update_fiscal_profile":
							tool_result = await tool_executor(user_id=user_id, db_client=db_client, **function_args)
						else:
							tool_result = await tool_executor(**function_args)
					else:
						logger.warning(f"Unknown function: {function_name}")
						tool_result = {"success": False, "error": f"Unknown function: {function_name}"}

					logger.info(f"Tool result success: {tool_result.get('success')}")

					# Emit tool result event (for SSE streaming)
					if progress_callback:
						await progress_callback.tool_result(function_name, tool_result.get('success', False))

					# Append each tool result as a separate tool message
					tool_response_content = tool_result.get('formatted_response', json.dumps(tool_result))
					# Protect tool results: force the model to present all numeric data
					tool_response_content += (
						"\n\n---\n[INSTRUCCION: Presenta TODAS las cifras de arriba en tu respuesta. "
						"Usa tabla markdown para el desglose. NO resumas ni parafrasees datos numericos.]"
					)
					messages.append({
						"role": "tool",
						"tool_call_id": tool_call.id,
						"content": tool_response_content
					})

				# Keep a reference to the last tool_result for the fallback logic below
				# (tool_result is still in scope from the last loop iteration)
				
				# Second call to get final response — STREAM token by token
				logger.info("Calling OpenAI again with tool result (streaming)")
				if progress_callback:
					await progress_callback.thinking("Redactando la respuesta...")

				try:
					content = await self._stream_openai_response(
						messages=messages,
						model=selected_model,
						progress_callback=progress_callback
					)
					# If stream produced very little content but we have a rich
					# formatted_response from the tool, prefer the tool result.
					# This handles the case where the stream stalls mid-response
					# (e.g., model writes "Ahora calculo..." then hangs).
					formatted = tool_result.get('formatted_response', '')
					if formatted and len(content) < len(formatted) * 0.5:
						logger.warning(
							f"⚠️ Stream content ({len(content)} chars) much shorter "
							f"than tool result ({len(formatted)} chars) — using tool result"
						)
						content = formatted
					if not content:
						content = formatted
				except asyncio.TimeoutError:
					logger.error("⏱️ Second OpenAI call timed out")
					content = tool_result.get('formatted_response', '')
					if not content:
						content = "Lo siento, el análisis está tardando más de lo esperado. Intenta reformular tu pregunta."
				logger.info(f"Final content length: {len(content)}")
			else:
				# No function call — STREAM direct response token by token
				content = message.content or ""
				finish_reason = response.choices[0].finish_reason

				# Apply post-LLM filter BEFORE streaming to user
				content = self._filter_bad_responses(content, query)

				if content and progress_callback:
					# Stream the already-received content chunk by chunk
					if progress_callback:
						await progress_callback.thinking("Redactando la respuesta...")
					await self._emit_content_chunks(content, progress_callback)

				if not content:
					logger.warning(f"No content in response. Finish reason: {finish_reason}")

				logger.info(f"Direct response content length: {len(content)}")
			
			# Validate output format — log warning but do NOT nuke the response
			# (B-CHAT-01 fix: replacing the entire response caused valid answers to be lost)
			from app.security.guardrails import guardrails_system
			if not guardrails_system.validate_output_format(content):
				logger.warning("⚠️ Internal JSON-like pattern detected in response (not replacing — may be legitimate content)")
			
			# === SPEED: Store successful response in Semantic Cache ===
			# Skip caching responses that indicate RAG failure (prevents poisoning)
			_nocache_patterns = ["no he encontrado datos", "te recomiendo consultar directamente", "no dispongo de información"]
			should_cache = not any(p in (content or "").lower() for p in _nocache_patterns)
			if should_cache:
				try:
					from app.security.semantic_cache import get_semantic_cache
					semantic_cache = get_semantic_cache()
					await semantic_cache.store(query, content)
				except Exception as e:
					logger.debug(f"Failed to cache response: {e}")
			else:
				print(f"🚫 NOT caching RAG-failure response (contains bad pattern)", flush=True)
			
			# Post-LLM filter: detect and block permission-asking or empty responses
			content = self._filter_bad_responses(content, query)

			return AgentResponse(
				content=content,
				sources=sources or [],
				metadata={
					"model": selected_model,  # ← Model actually used (from router)
					"base_model": self.model,  # Original model from settings
					"agent": self.name,
					"framework": "openai-api",
					"tool_used": bool(message.tool_calls),
					"current_year": self.current_year,
					"irpf_fiscal_year": self.irpf_fiscal_year,
					"autonomous_quota_year": self.autonomous_quota_year,
					"reasoning_effort": reasoning_effort,
					"router_confidence": router_confidence
				},
				agent_name=self.name
			)
			
		except asyncio.TimeoutError:
			# This catch is for outer-level timeout (shouldn't reach here normally)
			logger.error("⏱️ TaxAgent execution timeout")
			return AgentResponse(
				content="⏱️ Lo siento, el análisis está tardando más de lo esperado. Por favor, intenta reformular tu pregunta o simplificarla.",
				sources=sources or [],
				metadata={"error": "timeout"},
				agent_name=self.name
			)
		except Exception as e:
			logger.error(f"Agent execution error: {e}", exc_info=True)
			return AgentResponse(
				content=f"Error al procesar la consulta: {str(e)}",
				sources=[],
				metadata={"error": str(e)},
				agent_name=self.name
			)
	
	async def _stream_openai_response(
		self,
		messages: List[dict],
		model: str,
		progress_callback: Optional[Any] = None,
		timeout: float = 60.0,
		chunk_timeout: float = 30.0
	) -> str:
		"""
		Call OpenAI with stream=True and emit content_chunk events in real-time.

		Uses AsyncOpenAI + async for to avoid blocking the event loop,
		which would prevent sse_generator from yielding events to the client.

		Implements per-chunk timeout to prevent hanging when OpenAI stream
		stalls mid-response (known issue: openai-python #2725, #1134, #769).

		Returns the full accumulated content string.
		"""
		accumulated = []

		try:
			stream = await asyncio.wait_for(
				self._async_client.chat.completions.create(
					model=model,
					messages=messages,
					temperature=1,
					max_completion_tokens=10000,
					stream=True
				),
				timeout=timeout
			)

			# Iterate through streaming chunks with per-chunk timeout.
			# The SDK's async iterator has NO built-in timeout between chunks.
			# If OpenAI stalls mid-stream (after sending some tokens), the
			# async for loop hangs forever. We wrap each anext() in wait_for.
			# See: https://community.openai.com/t/468299
			buffer = ""
			CHUNK_SIZE = 12  # Send every ~12 chars (roughly 2-3 words)
			stream_iter = stream.__aiter__()

			while True:
				try:
					chunk = await asyncio.wait_for(
						stream_iter.__anext__(),
						timeout=chunk_timeout
					)
				except StopAsyncIteration:
					break
				except asyncio.TimeoutError:
					logger.warning(
						f"⏱️ No chunk received in {chunk_timeout}s — "
						f"stream stalled after {len(accumulated)} chunks "
						f"({sum(len(c) for c in accumulated)} chars)"
					)
					break

				delta = chunk.choices[0].delta if chunk.choices else None
				if delta and delta.content:
					buffer += delta.content
					accumulated.append(delta.content)

					if len(buffer) >= CHUNK_SIZE:
						if progress_callback:
							await progress_callback.content_chunk(buffer)
						buffer = ""

			# Flush remaining buffer
			if buffer and progress_callback:
				await progress_callback.content_chunk(buffer)

		except asyncio.TimeoutError:
			logger.error("⏱️ Streaming OpenAI call creation timed out")
			raise
		except Exception as e:
			logger.error(f"Streaming error: {e}", exc_info=True)
			# If we have partial content, return it
			if accumulated:
				logger.info(f"Returning partial content ({len(accumulated)} chunks)")
			else:
				raise

		return "".join(accumulated)

	async def _emit_content_chunks(self, content: str, progress_callback: Any) -> None:
		"""
		Emit already-generated content as chunks for real-time display.
		Used when the first OpenAI call returns content directly (no tool call).
		"""
		CHUNK_SIZE = 12
		for i in range(0, len(content), CHUNK_SIZE):
			chunk = content[i:i + CHUNK_SIZE]
			await progress_callback.content_chunk(chunk)
			# Tiny yield to allow SSE event queue to flush
			await asyncio.sleep(0.01)

	def _build_prompt(self, query: str, context: Optional[str] = None, user_memory_context: Optional[str] = None, fiscal_profile: Optional[Dict[str, Any]] = None) -> str:
		"""Build the user prompt with optional context and user memory."""

		query_lower = query.lower()
		requires_tool_hint = ""

		# Determine user employment status from fiscal profile (roles are additive)
		situacion = (fiscal_profile or {}).get("situacion_laboral", "").lower() if fiscal_profile else ""
		fp_roles = (fiscal_profile or {}).get("roles_adicionales", []) if fiscal_profile else []
		if isinstance(fp_roles, str):
			import json as _json2
			try:
				fp_roles = _json2.loads(fp_roles)
			except Exception:
				fp_roles = []
		is_autonomo = situacion in ("autónomo", "autonomo", "pluriactividad") or "creador_contenido" in fp_roles or "pluriactividad" in fp_roles

		if any(kw in query_lower for kw in ["cuota", "cotiza", "autónomo", "autonomo", "pago como"]):
			if any(char.isdigit() for char in query):
				if is_autonomo:
					requires_tool_hint = f"\nUSA calculate_autonomous_quota (año {self.autonomous_quota_year}).\n"
				else:
					requires_tool_hint = f"\nSituación laboral registrada: '{situacion or 'desconocida'}'. Pregunta si está dado de alta como autónomo antes de calcular.\n"

		if any(kw in query_lower for kw in ["irpf", "renta", "cuánto pago de impuestos", "cuanto pago de impuestos", "tributar", "tributo", "retención", "retencion"]):
			if any(char.isdigit() for char in query):
				ccaa = (fiscal_profile or {}).get("ccaa_residencia", "")
				if ccaa:
					requires_tool_hint = f'\nUSA simulate_irpf con ccaa="{ccaa}" y los ingresos del usuario.\n'
				else:
					requires_tool_hint = "\nUSA simulate_irpf. Si no conoces la CCAA, pregúntala antes de calcular.\n"

		if any(kw in query_lower for kw in ["deduccion", "deducción", "desgravacion", "desgravación", "deducir", "desgravar", "ahorrar en la renta", "ahorro fiscal", "deducciones"]):
			ccaa_hint = (fiscal_profile or {}).get("ccaa_residencia", "")
			if ccaa_hint:
				requires_tool_hint = f'\nUSA discover_deductions con ccaa="{ccaa_hint}" y los datos del perfil en answers.\n'
			else:
				requires_tool_hint = "\nUSA discover_deductions. Si conoces la CCAA del usuario, pásala. Si no, pregúntala.\n"

		critical_instructions = (
			"INSTRUCCIONES:\n"
			"1. RESPONDE a lo que el usuario pregunta — no calcules IRPF ni deducciones si no lo piden.\n"
			"2. USA herramientas SOLO cuando la pregunta lo requiera (IRPF, cuota, deducciones, IVA, ISD).\n"
			"3. Si usas una herramienta, presenta los resultados con cifras exactas en tabla markdown.\n"
			"4. Si falta un dato crítico para responder, pregunta ESO y solo eso.\n"
			"5. Responde en lenguaje natural. Aviso orientativo al final (1 línea).\n"
			"6. Si la pregunta es informativa (qué es X, cómo funciona Y, qué epígrafe), responde con tu conocimiento directamente."
		)

		if context:
			return f"""{requires_tool_hint}Información de la base de conocimiento fiscal (AEAT, BOE, normativas forales):

{context}

---

Pregunta: {query}

{critical_instructions}"""
		else:
			if requires_tool_hint:
				return f"{requires_tool_hint}\nPregunta: {query}\n\n{critical_instructions}"
			return f"Pregunta: {query}\n\n{critical_instructions}"
	
	async def ask(self, question: str, context: Optional[str] = None) -> str:
		"""
		Convenience method for asking questions.
		
		Args:
			question: User's question  
			context: Retrieved context from RAG
			
		Returns:
			str: Answer text
		"""
		response = await self.run(query=question, context=context)
		return response.content
	
	def run_sync(
		self,
		query: str,
		context: Optional[str] = None,
		sources: Optional[List[Dict[str, Any]]] = None
	) -> AgentResponse:
		"""
		Synchronous version of run() for non-async contexts.
		"""
		import asyncio
		
		try:
			loop = asyncio.get_event_loop()
		except RuntimeError:
			loop = asyncio.new_event_loop()
			asyncio.set_event_loop(loop)
		
		return loop.run_until_complete(self.run(query, context, sources))


# Global agent instance
_tax_agent: Optional[TaxAgent] = None


def get_tax_agent() -> TaxAgent:
	"""
	Get the global TaxAgent instance.
	
	Returns:
		TaxAgent instance
	"""
	global _tax_agent
	
	if _tax_agent is None:
		_tax_agent = TaxAgent()
	
	return _tax_agent

def format_sources_inline(sources: Optional[List[Dict[str, Any]]]) -> str:
	"""
	Format sources as inline compact text (no bullets).
	
	Groups by document and aggregates page numbers.
	Example: "Manual IRPF 2024 (págs. 45, 67), Ley 35/2006 (pág. 12)"
	
	Args:
		sources: List of source dicts with 'document' and 'page' keys
		
	Returns:
		Formatted string or empty string if no sources
	"""
	if not sources:
		return ""
	
	# Group sources by document
	doc_pages = {}
	for source in sources:
		doc_name = source.get("document", "Documento desconocido")
		page = source.get("page", 0)
		
		# Clean document name (remove extensions)
		clean_name = doc_name.replace('.pdf', '').replace('.md', '').strip()
		
		if clean_name not in doc_pages:
			doc_pages[clean_name] = []
		doc_pages[clean_name].append(page)
	
	# Format as inline list
	formatted_sources = []
	for doc_name, pages in doc_pages.items():
		# Sort and deduplicate pages
		unique_pages = sorted(set(p for p in pages if p > 0))
		
		if not unique_pages:
			continue
		
		# Format page numbers
		if len(unique_pages) == 1:
			page_str = f"pág. {unique_pages[0]}"
		elif len(unique_pages) <= 4:
			page_str = f"págs. {', '.join(map(str, unique_pages))}"
		else:
			# Too many pages, show first 3 + "..."
			page_str = f"págs. {', '.join(map(str, unique_pages[:3]))}..."
		
		formatted_sources.append(f"{doc_name} ({page_str})")
	
	if not formatted_sources:
		return ""
	
	# Join with commas
	sources_text = ", ".join(formatted_sources)
	
	return f"\n\n📄 **Fuentes**: {sources_text}"