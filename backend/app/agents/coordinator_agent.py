"""
CoordinatorAgent - Multi-Agent Orchestrator

Routes user queries to the appropriate specialist agent.
"""
import logging
from typing import Dict, Any, Optional

from agent_framework import ChatAgent, Workflow
from agent_framework.openai import OpenAIChatClient
from app.agents.tax_agent import get_tax_agent
from app.agents.payslip_agent import get_payslip_agent

logger = logging.getLogger(__name__)


class CoordinatorAgent:
	"""
	Orchestrates multiple specialist agents.
	
	Routes queries to:
	- TaxAgent: For general tax questions, IRPF, autonomous quotas
	- PayslipAgent: For payslip analysis and interpretation
	"""
	
	def __init__(self):
		"""Initialize coordinator with workflow"""
		
		# Get specialist agents
		self.tax_agent = get_tax_agent()
		self.payslip_agent = get_payslip_agent()
		
		# Create router agent (decides which specialist to use)
		import os
		chat_client = OpenAIChatClient(
			model_id=os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
		)
		
		self.router = ChatAgent(
			chat_client=chat_client,
			name="Router",
			instructions="""Eres un router inteligente que decide qué agente especializado debe responder.

Tienes 2 agentes disponibles:
1. **TaxAgent**: Experto en fiscalidad española (IRPF, cuotas autónomos, deducciones, modelos tributarios)
2. **PayslipAgent**: Experto en análisis de nóminas (interpretación, conceptos salariales, retenciones)

## Reglas de enrutamiento:

**Usa TaxAgent cuando:**
- Pregunten sobre IRPF, declaración de la renta
- Calculen cuotas de autónomos
- Pregunten por deducciones fiscales
- Mencionen modelos tributarios (130, 303, etc.)
- Pregunten por tramos de IRPF o tipos impositivos
- Temas generales de fiscalidad

**Usa PayslipAgent cuando:**
- Analicen una nómina específica
- Pregunten por conceptos de nómina (salario base, complementos, pagas extras)
- Interpreten retenciones en nómina
- Comparen nóminas entre periodos
- Pregunten por cotizaciones a la Seguridad Social en nómina

Responde SOLO con: "TaxAgent" o "PayslipAgent"."""
		)
		
		logger.info("CoordinatorAgent initialized with TaxAgent and PayslipAgent")
	
	async def route(self, query: str) -> str:
		"""
		Route query to appropriate agent.
		
		Args:
			query: User's question
			
		Returns:
			Agent name ("TaxAgent" or "PayslipAgent")
		"""
		try:
			response = await self.router.run(f"Query: {query}")
			agent_name = response.text.strip()
			
			if agent_name not in ["TaxAgent", "PayslipAgent"]:
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
			context: Additional context (payslip data, RAG results, etc.)
			
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
		
		# Otherwise, use router to decide
		agent_name = await self.route(query)
		
		if agent_name == "PayslipAgent":
			return await self.payslip_agent.run(query=query)
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