"""
CoordinatorAgent - Multi-Agent Orchestrator

Routes user queries to the appropriate specialist agent.
"""
import logging
from typing import Dict, Any, Optional

try:
    from agent_framework import ChatAgent, Workflow
    from agent_framework.openai import OpenAIChatClient
    AGENT_FRAMEWORK_AVAILABLE = True
except Exception:
    AGENT_FRAMEWORK_AVAILABLE = False
    ChatAgent = None
    Workflow = None
    OpenAIChatClient = None
from app.agents.tax_agent import get_tax_agent
from app.agents.payslip_agent import get_payslip_agent
from app.agents.workspace_agent import get_workspace_agent
from app.agents.competitor_analysis_agent import get_competitor_analysis_agent

logger = logging.getLogger(__name__)


class CoordinatorAgent:
	"""
	Orchestrates multiple specialist agents.

	Routes queries to:
	- TaxAgent: For general tax questions, IRPF, autonomous quotas
	- PayslipAgent: For payslip analysis and interpretation
	- WorkspaceAgent: For analyzing user's uploaded documents
	- CompetitorAnalysisAgent: For competitive intelligence and market analysis
	"""

	def __init__(self):
		"""Initialize coordinator with workflow"""

		# Get specialist agents
		self.tax_agent = get_tax_agent()
		self.payslip_agent = get_payslip_agent()
		self.workspace_agent = get_workspace_agent()
		self.competitor_agent = get_competitor_analysis_agent()

		# Create router agent (decides which specialist to use)
		from app.config import settings
		chat_client = OpenAIChatClient(
			model_id=settings.OPENAI_MODEL
		)

		self.router = ChatAgent(
			chat_client=chat_client,
			name="Router",
			instructions="""Eres un router inteligente que decide qué agente especializado debe responder.

Tienes 4 agentes disponibles:
1. **TaxAgent**: Experto en fiscalidad española (IRPF, cuotas autónomos, deducciones, modelos tributarios)
2. **PayslipAgent**: Experto en análisis de nóminas (interpretación, conceptos salariales, retenciones)
3. **WorkspaceAgent**: Analiza archivos del espacio de trabajo del usuario (facturas, nóminas, declaraciones)
4. **CompetitorAnalysisAgent**: Analiza la competencia (TaxDown, Declarando, etc.) y posición de mercado

## Reglas de enrutamiento:

**Usa TaxAgent cuando:**
- Pregunten sobre IRPF, declaración de la renta
- Calculen cuotas de autónomos
- Pregunten por deducciones fiscales
- Mencionen modelos tributarios (130, 303, etc.)
- Pregunten por tramos de IRPF o tipos impositivos
- Temas generales de fiscalidad
- Pregunten sobre fiscalidad de creadores, influencers, YouTubers, streamers, TikTokers
- Mencionen plataformas (YouTube, TikTok, Twitch, Instagram, Patreon, OnlyFans)
- Pregunten sobre Modelo 349, intracomunitarias, DAC7
- Pregunten sobre epigrafe IAE o alta como autonomo

**Usa PayslipAgent cuando:**
- Analicen una nómina específica
- Pregunten por conceptos de nómina (salario base, complementos, pagas extras)
- Interpreten retenciones en nómina
- Comparen nóminas entre periodos
- Pregunten por cotizaciones a la Seguridad Social en nómina

**Usa WorkspaceAgent cuando:**
- Pregunten por "mis documentos", "mis archivos", "mi workspace"
- Pidan calcular IVA de "mis facturas"
- Pregunten por "mis nóminas" o proyecciones basadas en sus datos
- Mencionen plazos o fechas límite de declaraciones
- Quieran un resumen de sus archivos fiscales
- Pregunten sobre balance de IVA soportado/repercutido

**Usa CompetitorAnalysisAgent cuando:**
- Mencionen TaxDown, Declarando, Taxfix, Xolo u otros competidores
- Pregunten por comparativas de funcionalidades o precios
- Pidan análisis de mercado, DAFO, posicionamiento
- Pregunten por integración con AEAT (Colaborador Social)
- Pidan sugerencias de mejora o roadmap de producto
- Pregunten qué hace la competencia mejor o peor
- Mencionen "competencia", "mercado", "comparar", "ventajas", "huecos"

Responde SOLO con: "TaxAgent", "PayslipAgent", "WorkspaceAgent" o "CompetitorAnalysisAgent"."""
		)

		logger.info("CoordinatorAgent initialized with TaxAgent, PayslipAgent, WorkspaceAgent, and CompetitorAnalysisAgent")
	
	async def route(self, query: str) -> str:
		"""
		Route query to appropriate agent.

		Args:
			query: User's question

		Returns:
			Agent name ("TaxAgent", "PayslipAgent", or "WorkspaceAgent")
		"""
		try:
			response = await self.router.run(f"Query: {query}")
			agent_name = response.text.strip()

			if agent_name not in ["TaxAgent", "PayslipAgent", "WorkspaceAgent", "CompetitorAnalysisAgent"]:
				# Default to TaxAgent if unclear
				logger.warning(f"Unclear routing: {agent_name}, defaulting to TaxAgent")
				return "TaxAgent"

			logger.info(f"Routed to: {agent_name}")
			return agent_name

		except Exception as e:
			logger.error(f"Routing error: {e}", exc_info=True)
			return "TaxAgent"  # Default
	
	async def run(
		self,
		query: str,
		context: Dict[str, Any] = None
	):
		"""
		Run coordinator: route and execute appropriate agent.

		Args:
			query: User's question
			context: Additional context (payslip data, RAG results, workspace data, etc.)

		Returns:
			AgentResponse from the selected specialist
		"""
		# Detect if query is about a specific payslip
		if context and context.get("payslip_data"):
			# Direct to PayslipAgent
			logger.info("Detected payslip context, routing to PayslipAgent")
			return await self.payslip_agent.analyze(
				payslip_data=context["payslip_data"],
				user_question=query
			)

		# Detect if workspace context is provided
		if context and context.get("workspace_context"):
			# Direct to WorkspaceAgent
			logger.info("Detected workspace context, routing to WorkspaceAgent")
			return await self.workspace_agent.run(
				query=query,
				context=context.get("workspace_context"),
				sources=context.get("sources"),
				workspace_id=context.get("workspace_id"),
				user_id=context.get("user_id")
			)

		# Otherwise, use router to decide
		agent_name = await self.route(query)

		if agent_name == "PayslipAgent":
			return await self.payslip_agent.run(query=query)
		elif agent_name == "WorkspaceAgent":
			# WorkspaceAgent without explicit context
			workspace_context = context.get("workspace_context") if context else None
			return await self.workspace_agent.run(
				query=query,
				context=workspace_context or "",
				user_id=context.get("user_id") if context else None
			)
		elif agent_name == "CompetitorAnalysisAgent":
			return await self.competitor_agent.run(
				query=query,
				context=context.get("rag_context") if context else None,
				sources=context.get("sources") if context else None,
			)
		else:
			# TaxAgent (with RAG context if available)
			rag_context = context.get("rag_context") if context else None
			sources = context.get("sources") if context else None
			return await self.tax_agent.run(
				query=query,
				context=rag_context,
				sources=sources
			)


# Global instance
_coordinator: CoordinatorAgent = None


def get_coordinator() -> CoordinatorAgent:
	"""Get the global CoordinatorAgent instance"""
	global _coordinator
	
	if _coordinator is None:
		_coordinator = CoordinatorAgent()
	
	return _coordinator