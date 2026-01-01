"""
Base Agent Wrapper for Microsoft Agent Framework
Provides a unified interface for all agents
"""
import os
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from agent_framework import ChatAgent
from agent_framework.openai import OpenAIChatClient

logger = logging.getLogger(__name__)


@dataclass
class AgentResponse:
	"""Unified response structure"""
	content: str
	sources: List[Dict[str, Any]]
	metadata: Dict[str, Any]
	agent_name: str


class BaseAgent:
	"""
	Base class for all Impuestify agents using Agent Framework.
	
	Provides:
	- Unified OpenAI client setup
	- Tool registration
	- Response formatting
	- Error handling
	"""
	
	def __init__(
		self,
		name: str,
		instructions: str,
		tools: Optional[List] = None,
		model: Optional[str] = None
	):
		"""
		Initialize base agent.
		
		Args:
			name: Agent name
			instructions: System prompt/instructions
			tools: List of tools (functions) the agent can use
			model: OpenAI model name
		"""
		self.name = name
		self.instructions = instructions
		self.model = model or os.environ.get("OPENAI_MODEL", "gpt-5-mini")
		
		# Create OpenAI chat client
		chat_client = OpenAIChatClient(
			api_key=os.environ.get("OPENAI_API_KEY"),
			model_id=self.model
		)
		
		# Create Agent Framework agent
		self.agent = ChatAgent(
			chat_client=chat_client,
			name=name,
			instructions=instructions,
			tools=tools or []
		)
		
		logger.info(f"Agent '{name}' initialized with Agent Framework (model: {self.model})")
	
	async def run(
		self,
		query: str,
		context: Optional[str] = None,
		sources: Optional[List[Dict[str, Any]]] = None,
		**kwargs
	) -> AgentResponse:
		"""
		Run the agent with a query.
		
		Args:
			query: User's question
			context: Additional context (e.g., RAG results)
			sources: Source documents for citations
			**kwargs: Additional parameters
			
		Returns:
			AgentResponse with formatted output
		"""
		try:
			# Build full prompt with context if provided
			if context:
				full_query = f"{context}\n\n---\n\nUser query: {query}"
			else:
				full_query = query
			
			# Run agent (Agent Framework handles tools automatically)
			response = await self.agent.run(full_query)
			
			return AgentResponse(
				content=response.text,
				sources=sources or [],
				metadata={
					"model": self.model,
					"agent": self.name,
					"framework": "microsoft-agent-framework"
				},
				agent_name=self.name
			)
		
		except Exception as e:
			logger.error(f"Agent '{self.name}' execution error: {e}", exc_info=True)
			return AgentResponse(
				content=f"Error al procesar la consulta: {str(e)}",
				sources=[],
				metadata={"error": str(e)},
				agent_name=self.name
			)
	
	async def run_stream(self, query: str, context: Optional[str] = None):
		"""
		Run agent with streaming response.
		
		Args:
			query: User's question
			context: Additional context
			
		Yields:
			Chunks of response text
		"""
		try:
			if context:
				full_query = f"{context}\n\n---\n\nUser query: {query}"
			else:
				full_query = query
			
			async for chunk in self.agent.run_stream(full_query):
				if chunk.text:
					yield chunk.text
		
		except Exception as e:
			logger.error(f"Agent streaming error: {e}", exc_info=True)
			yield f"Error: {str(e)}"